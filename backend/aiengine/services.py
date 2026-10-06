"""
Orchestration: combine prompts.py + providers.py with the Django models.
Views call these; they stay thin and testable independent of HTTP.

Every function that calls a Claude/OpenAI provider follows the same shape:
check_ai_allowed(workspace) -> providers call -> record_ai_cost(workspace, cost).
"""
from datetime import datetime
from django.utils import timezone
from django.core.files.base import ContentFile

from . import prompts, providers
from django.conf import settings
from billing.usage import check_ai_allowed, check_feature_allowed, is_feature_enabled, feature_tier_value, record_ai_cost


def _text_model():
    if (settings.TEXT_PROVIDER or 'claude').lower() == 'openai':
        return settings.OPENAI_TEXT_MODEL
    return providers.get_claude_model()


# ---------- Onboarding / brand ----------

def summarize_website(brand):
    if not brand.company_website:
        return
    raw = providers.fetch_url_text(brand.company_website)
    if not raw:
        return
    workspace = brand.workspace
    check_ai_allowed(workspace)
    system, user = prompts.website_summary_prompt(brand.company_website, raw)
    out, cost = providers.text_json(system, user, max_tokens=400)
    record_ai_cost(workspace, cost, purpose="website_summary", model=_text_model())
    brand.website_summary = out.get("summary", "")
    brand.save(update_fields=["website_summary"])


def generate_onboarding_preview(brand):
    workspace = brand.workspace
    check_ai_allowed(workspace)
    sample_posts = list(workspace.past_posts.order_by("-posted_on").values_list("text", flat=True)[:5])
    system, user = prompts.onboarding_preview_prompt(brand, sample_posts)
    out, cost = providers.text_json(system, user, max_tokens=700)
    record_ai_cost(workspace, cost, purpose="onboarding_preview", model=_text_model())
    brand.tone_sample_post = out.get("sample_post", "")
    brand.save(update_fields=["tone_sample_post"])
    return out


def analyze_tone(workspace):
    from content.models import Post
    posted = list(Post.objects.filter(workspace=workspace, status="posted").exclude(text="").order_by("-posted_at")[:15])
    if not posted:
        raise providers.AIError("Mark at least one post as posted first.")
    check_feature_allowed(workspace, "tone_analysis")
    system, user_msg = prompts.tone_analysis_prompt(posted)
    out, cost = providers.text_json(system, user_msg, max_tokens=900)
    record_ai_cost(workspace, cost, purpose="tone_analysis", model=_text_model())
    brand = workspace.brand_profile
    brand.tone_summary = out.get("summary", "")
    brand.tone_traits = out.get("traits", [])
    brand.tone_language = out.get("language", "")
    brand.tone_analyzed_at = timezone.now()
    brand.tone_posts_analyzed = len(posted)
    brand.save()
    return brand


def suggest_topics(workspace):
    from content.models import Post
    brand = workspace.brand_profile
    check_feature_allowed(workspace, "topic_suggestions")
    horizon = feature_tier_value(workspace, "future_planning_horizon")
    top = list(Post.objects.filter(workspace=workspace, status="posted").order_by("-likes")[:3])
    system, user_msg = prompts.topic_suggestion_prompt(brand, top, horizon=horizon)
    out, cost = providers.text_json(system, user_msg, max_tokens=900)
    record_ai_cost(workspace, cost, purpose="topic_suggestions", model=_text_model())
    return out.get("topics", [])


# ---------- Strategy / calendar ----------

def generate_calendar(plan):
    workspace = plan.workspace
    brand = workspace.brand_profile
    check_feature_allowed(workspace, "calendar_builder")
    smart_scheduling = is_feature_enabled(workspace, "smart_day_scheduling")
    blocked = list(workspace.blocked_dates.filter(date__range=(plan.start_date, plan.end_date)).values_list("date", flat=True))
    system, user_msg = prompts.calendar_prompt(brand, plan, [d.isoformat() for d in blocked], smart_scheduling=smart_scheduling)
    out, cost = providers.text_json(system, user_msg, max_tokens=2000)
    record_ai_cost(workspace, cost, purpose="calendar_builder", model=_text_model())

    from content.models import PlannedItem
    plan.items.all().delete()
    items = []
    for i, it in enumerate(out.get("items", [])):
        try:
            date_str = it.get("date")
            time_str = it.get("time") or "09:00"
            when = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").date()
        except (ValueError, TypeError):
            continue
        items.append(PlannedItem(
            plan=plan, title=it.get("title", "")[:300], angle=it.get("angle", ""),
            item_type="article" if it.get("item_type") == "article" else "post",
            suggested_date=when, date_rationale=it.get("date_rationale", ""), order=i,
        ))
    PlannedItem.objects.bulk_create(items)
    plan.status = "proposed"
    plan.save(update_fields=["status"])
    return plan.items.all()


def generate_draft_for_item(item):
    from content.models import Post
    workspace = item.plan.workspace
    brand = workspace.brand_profile
    check_feature_allowed(workspace, "draft_generation")
    system, user_msg = prompts.draft_prompt(brand, item.item_type, item.title, item.angle)
    out, cost = providers.text_json(system, user_msg, max_tokens=4000)
    record_ai_cost(workspace, cost, purpose="draft_generation", model=_text_model())

    post, _ = Post.objects.update_or_create(
        planned_item=item,
        defaults=dict(
            workspace=workspace, plan=item.plan, type=item.item_type, title=item.title,
            text=out.get("text", ""), hashtags=out.get("hashtags", ""),
            status="pending_approval",
            predicted_score=out.get("potential_score"), predicted_reason=out.get("potential_reason", ""),
            scheduled_at=timezone.make_aware(datetime.combine(item.suggested_date, datetime.min.time().replace(hour=9))),
        ),
    )
    image_brief = out.get("image_brief", "")
    if image_brief:
        try:
            generate_post_image(post, image_brief)
        except providers.AIError:
            pass  # drafting still succeeds even if image generation fails or budget is tight
    return post


# ---------- Per-post AI actions ----------

def predict_potential(post):
    workspace = post.workspace
    brand = workspace.brand_profile
    check_ai_allowed(workspace)
    system, user_msg = prompts.potential_prompt(brand, post)
    out, cost = providers.text_json(system, user_msg, max_tokens=500)
    record_ai_cost(workspace, cost, purpose="predict_potential", model=_text_model())
    post.predicted_score = max(1, min(10, round(out.get("score", 5))))
    post.predicted_reason = out.get("reason", "")
    post.predicted_tip = out.get("tip", "")
    post.save(update_fields=["predicted_score", "predicted_reason", "predicted_tip"])
    return post


def suggest_reply(comment):
    workspace = comment.post.workspace
    brand = workspace.brand_profile
    check_feature_allowed(workspace, "reply_suggestions")
    system, user_msg = prompts.reply_prompt(brand, comment.post, comment)
    out, cost = providers.text_json(system, user_msg, max_tokens=400)
    record_ai_cost(workspace, cost, purpose="reply_suggestions", model=_text_model())
    comment.reply = out.get("reply", "")
    comment.reply_generated_at = timezone.now()
    comment.save(update_fields=["reply", "reply_generated_at"])
    return comment


def suggest_next_step(post):
    workspace = post.workspace
    brand = workspace.brand_profile
    check_ai_allowed(workspace)
    system, user_msg = prompts.next_step_prompt(brand, post, list(post.comments.all()))
    out, cost = providers.text_json(system, user_msg, max_tokens=500)
    record_ai_cost(workspace, cost, purpose="next_step", model=_text_model())
    post.next_step_suggestion = out.get("suggestion", "")
    post.next_step_at = timezone.now()
    post.save(update_fields=["next_step_suggestion", "next_step_at"])
    return post


def generate_post_image(post, brief: str):
    workspace = post.workspace
    check_feature_allowed(workspace, "image_generation")
    style_note = " Clean, professional, editorial style suited to LinkedIn; no embedded text, no logos, no real identifiable people."
    image_bytes, cost = providers.generate_image_bytes(brief + style_note)
    record_ai_cost(workspace, cost, purpose="image_generation", model=settings.OPENAI_IMAGE_MODEL)
    img = post.images.create(prompt=brief, source="generated")
    img.image.save(f"post_{post.id}_{img.id}.png", ContentFile(image_bytes), save=True)
    return img


# ---------- Dashboard analysis ----------

def analyze_performance(workspace):
    from content.models import Post
    posts = list(Post.objects.filter(workspace=workspace, status="posted").order_by("-posted_at")[:10])
    if not posts:
        raise providers.AIError("No posted posts yet to analyze.")
    summary = "\n".join(f'- "{p.title or p.text[:60]}" ({p.posted_at:%Y-%m-%d}): {p.likes} likes, {p.comments.count()} comments' for p in posts)
    goal = workspace.goals.filter(is_active=True).first()
    goal_summary = f"{goal.title}: target {goal.target_value} {goal.metric} by {goal.end_date}" if goal else "(no active goal)"
    brand = workspace.brand_profile
    check_feature_allowed(workspace, "growth_analysis")
    system, user_msg = prompts.performance_analysis_prompt(brand, summary, goal_summary)
    out, cost = providers.text_json(system, user_msg, max_tokens=700)
    record_ai_cost(workspace, cost, purpose="growth_analysis", model=_text_model())
    return out
