# In-memory /check repeat state:
# {user_id: {"count": int, "last_commits": int, "last_time": float}}
USER_CHECK_STATE: dict[int, dict[str, int | float]] = {}
