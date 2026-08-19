from dataclasses import dataclass, field


def make_overview(repo_path: str = "Owner/Repo", **overrides) -> dict:
    data = {
        "repo_path": repo_path,
        "stars": 10,
        "forks": 3,
        "subscribers": 2,
        "open_prs": 4,
        "closed_prs": 5,
        "issues_enabled": True,
        "open_issues": 6,
        "closed_issues": 7,
        "default_branch": "main",
        "language": "Python",
        "license": "MIT",
        "pushed_at": "2026-08-18T04:00:00Z",
        "archived": False,
        "disabled": False,
    }
    data.update(overrides)
    return data


@dataclass
class FakeMessage:
    replies: list[dict] = field(default_factory=list)

    async def reply_text(self, text, **kwargs):
        self.replies.append({"text": text, **kwargs})


@dataclass
class FakeIdentity:
    id: int


class FakeUpdate:
    def __init__(self, user_id: int = 1, chat_id: int = 10):
        self.effective_user = FakeIdentity(user_id)
        self.effective_chat = FakeIdentity(chat_id)
        self.message = FakeMessage()


@dataclass
class FakeContext:
    args: list[str] = field(default_factory=list)
    bot: object | None = None
    job_queue: object | None = None
