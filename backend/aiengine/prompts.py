"""
Every prompt the platform sends to the text model, in one place, so tone,
rules and JSON shapes stay consistent and easy to tune.
"""


def persona_line(brand) -> str:
    ws = brand.workspace
    if ws.persona_type == "company":
        name = brand.company_name or ws.name
        return f"You are writing as the official LinkedIn voice of {name} — a company page, not a named individual. Speak as \"we\", representing the organization, never as a single founder."
    return f"You are writing as {ws.name}, posting in their own voice as an individual professional — first person, personal opinions and experience."


def voice_block(brand) -> str:
    parts = [persona_line(brand)]
    if brand.tone_summary:
        parts.append(f"Tone, learned from {brand.tone_posts_analyzed} of this person's posted posts: {brand.tone_summary}")
        if brand.tone_traits:
            parts.append(f"Traits: {', '.join(brand.tone_traits)}.")
        if brand.tone_language:
            parts.append(f"Language patterns: {brand.tone_language}")
    if brand.voice_notes:
        parts.append(f"Additional notes from the person: {brand.voice_notes}")
    return "\n".join(parts) if parts else "(No voice profile yet. Write clear, direct, plain-spoken content.)"


def strategy_block(brand) -> str:
    lines = []
    if brand.industry:
        lines.append(f"Industry: {brand.industry}")
    if brand.target_audience:
        lines.append(f"Target audience: {brand.target_audience}")
    if brand.core_topics:
        lines.append(f"Core topics: {brand.core_topics}")
    if brand.website_summary:
        lines.append(f"About the company (from their website): {brand.website_summary}")
    return "\n".join(lines) if lines else "(No audience or industry set yet — assume a general B2B professional audience.)"


def website_summary_prompt(url: str, raw_text: str) -> tuple[str, str]:
    system = ("You summarize a company website into context a LinkedIn ghostwriter can use. "
              "Be concrete: what the company does, who it serves, how it talks about itself. "
              "Return ONLY JSON, no markdown fences.")
    user = f"Website: {url}\n\nExtracted text:\n{raw_text[:6000]}\n\nJSON shape: {{\"summary\": \"3-5 sentences\"}}"
    return system, user


def onboarding_preview_prompt(brand, sample_posts: list[str]) -> tuple[str, str]:
    system = ("You are a LinkedIn ghostwriter previewing your work for a new client, based only on what "
              "they've told you so far. Write ONE short sample LinkedIn post that demonstrates the tone "
              "and language patterns described, on a topic relevant to their industry. "
              "Return ONLY JSON, no markdown fences.")
    history = ("\n\nTheir own past posts, for reference:\n" + "\n---\n".join(sample_posts[:5])) if sample_posts else ""
    user = f"<voice_profile>\n{voice_block(brand)}\n</voice_profile>\n\n<audience_and_industry>\n{strategy_block(brand)}\n</audience_and_industry>{history}\n\nJSON shape: {{\"sample_post\": \"the full post\", \"notes\": \"1-2 sentences on what you leaned into and why\"}}"
    return system, user


def tone_analysis_prompt(posts) -> tuple[str, str]:
    system = ("You analyze a person's own past LinkedIn posts to describe their tone and writing style "
              "precisely enough that new drafts could be written to match it convincingly. Be specific, not generic. "
              "Return ONLY JSON, no markdown fences.")
    body = "\n\n".join(f"--- Post {i+1} ({p.likes} likes) ---\n{p.text}" for i, p in enumerate(posts))
    user = (f"Here are my posted LinkedIn posts, most recent last:\n\n{body}\n\n"
            'JSON shape: {"summary":"2-3 sentences describing the overall tone and personality",'
            '"traits":["trait1","trait2","trait3","trait4"],'
            '"language":"notes on sentence length, formality, use of lists/questions/line breaks/hashtags/emoji"}')
    return system, user


def topic_suggestion_prompt(brand, top_performers) -> tuple[str, str]:
    history = ("What has worked before, best first:\n" + "\n".join(f'- "{p.title or p.text[:60]}" — {p.likes} likes' for p in top_performers)) \
        if top_performers else "(No performance history yet — recommend based on general best practice for this audience and industry.)"
    system = ("You are a LinkedIn content strategist. Recommend specific, concrete post topics and angles "
              "likely to perform well for this exact audience and industry — not generic advice. "
              "Return ONLY JSON, no markdown fences.")
    user = (f"<audience_and_industry>\n{strategy_block(brand)}\n</audience_and_industry>\n\n"
            f"<voice_profile>\n{voice_block(brand)}\n</voice_profile>\n\n{history}\n\n"
            "Suggest 5 topic ideas.\n"
            'JSON shape: {"topics":[{"title":"short topic name","angle":"the specific angle, hook or format","why":"why this should work for this audience and industry"}]}')
    return system, user


def calendar_prompt(brand, plan, blocked_dates: list[str]) -> tuple[str, str]:
    blocked = f"Do not schedule on these dates (holidays/leave): {', '.join(blocked_dates)}." if blocked_dates else "No dates are blocked."
    system = ("You are a LinkedIn content strategist and scheduler. Build a posting calendar: specific titles, "
              "a one-line angle for each, and a recommended posting date and time for each — spread sensibly "
              "across the window, generally favoring Tuesday-Thursday mid-morning as higher-engagement slots "
              "(note this is general best practice, not live platform data), and never on a blocked date or a weekend "
              "unless the window leaves no other choice. Return ONLY JSON, no markdown fences.")
    user = (f"<audience_and_industry>\n{strategy_block(brand)}\n</audience_and_industry>\n\n"
            f"<voice_profile>\n{voice_block(brand)}\n</voice_profile>\n\n"
            f"Subject/brief: {plan.subject}\n{plan.brief}\n\n"
            f"Window: {plan.start_date} to {plan.end_date}\n"
            f"Needed: {plan.num_posts} posts and {plan.num_articles} articles.\n{blocked}\n\n"
            'JSON shape: {"items":[{"title":"...","angle":"...","item_type":"post|article","date":"YYYY-MM-DD","time":"HH:MM","date_rationale":"one short reason for this date/time"}]}')
    return system, user


def draft_prompt(brand, item_type: str, title: str, angle: str) -> tuple[str, str]:
    is_article = item_type == "article"
    system = (f"You write LinkedIn {'articles' if is_article else 'posts'} in this person's voice, for a specific "
              "audience and industry.\n\n"
              f"<voice_profile>\n{voice_block(brand)}\n</voice_profile>\n\n"
              f"<audience_and_industry>\n{strategy_block(brand)}\n</audience_and_industry>\n\n"
              "Rules:\n"
              f"- {'Articles run 600-1200 words, with a clear structure and subheadings where useful.' if is_article else 'Posts run 900-1300 characters. Short paragraphs of 1-2 lines. Line 1 is a hook under 12 words that works before see more.'}\n"
              "- No filler intro, no corporate jargon, no invented statistics, client names or experiences — "
              "write [ADD DETAIL: what is needed] where a real detail is missing.\n"
              "- End with one natural question or takeaway, not a hard sell.\n"
              "- Suggest 3-5 relevant hashtags separately from the body.\n"
              "- Also write a one-sentence image brief describing a simple, tasteful visual that would suit this post "
              "(no text-in-image, no logos, no real people).\n"
              "- Estimate engagement potential for THIS audience and industry: 1 (unlikely to get traction) to 10 (strong potential).\n"
              "Return ONLY JSON, no markdown fences.")
    user = (f"Title: {title}\nAngle: {angle}\n\n"
            'JSON shape: {"text":"the body, without hashtags","hashtags":"#tag1 #tag2 #tag3","image_brief":"...","potential_score":7,"potential_reason":"one short sentence"}')
    return system, user


def potential_prompt(brand, post) -> tuple[str, str]:
    system = ("You estimate how well a LinkedIn post is likely to perform — in likes — for a specific audience and "
              "industry, based on patterns of high-performing content in that space (hook strength, format, "
              "specificity, relatability).\n\n"
              f"<audience_and_industry>\n{strategy_block(brand)}\n</audience_and_industry>\n\n"
              f"<voice_profile>\n{voice_block(brand)}\n</voice_profile>\nReturn ONLY JSON, no markdown fences.")
    user = f'Post:\n"""\n{post.text}\n"""\nHashtags: {post.hashtags or "(none)"}\n\nJSON shape: {{"score": 7, "reason": "1-2 sentences, specific to this post", "tip": "one concrete change that would likely raise the score"}}'
    return system, user


def reply_prompt(brand, post, comment) -> tuple[str, str]:
    system = ("You help reply to comments on this person's own LinkedIn posts, in their voice.\n\n"
              f"<voice_profile>\n{voice_block(brand)}\n</voice_profile>\n\n"
              "Rules: 1-3 sentences, specific to what they actually said — never generic (\"Thanks!\", \"Great point!\"). "
              "Warm, and keeps the conversation going where it fits. Never invent facts on this person's behalf; "
              "use [ADD DETAIL] if something specific is needed.\nReturn ONLY JSON, no markdown fences.")
    who = comment.person_name or "a commenter"
    if comment.person_title:
        who += f" ({comment.person_title})"
    user = f'My post:\n"""\n{post.text}\n"""\n\nComment from {who}:\n"""\n{comment.text}\n"""\n\nJSON shape: {{"reply":"the suggested reply"}}'
    return system, user


def next_step_prompt(brand, post, comments) -> tuple[str, str]:
    system = ("You analyze how one of this person's LinkedIn posts performed and suggest one concrete, specific "
              "next step — a content idea, a format change, or a follow-up action. Not generic social-media advice.\n\n"
              f"<voice_profile>\n{voice_block(brand)}\n</voice_profile>\nReturn ONLY JSON, no markdown fences.")
    comment_lines = "\n".join(f"- {c.person_name or 'Someone'}: {c.text}" for c in comments) or "(no comments yet)"
    user = (f'Post:\n"""\n{post.text}\n"""\n\nLikes: {post.likes}\nComments:\n{comment_lines}\n\n'
            'JSON shape: {"suggestion":"2-4 sentences, specific and actionable"}')
    return system, user


def performance_analysis_prompt(brand, posts_summary: str, goal_summary: str) -> tuple[str, str]:
    system = ("You are a LinkedIn growth analyst. Review this person's recent post performance and give a short, "
              "specific analysis: what is working, what isn't, and up to 3 concrete actions for the next two weeks. "
              "Ground every point in the actual numbers given — never generic advice.\nReturn ONLY JSON, no markdown fences.")
    user = (f"<audience_and_industry>\n{strategy_block(brand)}\n</audience_and_industry>\n\n"
            f"Recent posts:\n{posts_summary}\n\nActive goal:\n{goal_summary}\n\n"
            'JSON shape: {"headline":"one sentence verdict","whats_working":"2-3 sentences","whats_not":"2-3 sentences","actions":["action 1","action 2","action 3"]}')
    return system, user
