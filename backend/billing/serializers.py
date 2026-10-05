# Billing responses are plain dicts built by billing.usage (account_usage_summary,
# workspace_usage_summary) — their shape includes a nested per-workspace list that
# doesn't map cleanly onto a single flat serializer, so views return them directly.
