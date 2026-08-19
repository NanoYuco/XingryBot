import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from github import client


class FakeSessionContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeHttpResponse:
    def __init__(self, status, data, headers=None):
        self.status = status
        self._data = data
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def json(self, **_kwargs):
        return self._data


class FakeNetworkSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def response(status=200, data=None, headers=None):
    return client.GitHubResponse(status, data, headers or {})


def metadata(**overrides):
    value = {
        "full_name": "Owner/Repo",
        "private": False,
        "visibility": "public",
        "stargazers_count": 11,
        "forks_count": 4,
        "subscribers_count": 3,
        "has_issues": True,
        "default_branch": "main_branch",
        "language": "Python",
        "license": {"spdx_id": "MIT", "name": "MIT License"},
        "pushed_at": "2026-08-18T04:00:00Z",
        "archived": False,
        "disabled": False,
    }
    value.update(overrides)
    return value


def commit_at(value: datetime, index: int = 1):
    return {
        "sha": f"{index:040x}",
        "commit": {
            "committer": {"date": value.isoformat().replace("+00:00", "Z")},
            "message": f"change_{index}\nbody not displayed",
            "author": {"name": "A_[uthor]"},
        },
    }


def one_item_count(count: int):
    if count == 0:
        return response(data=[])
    if count == 1:
        return response(data=[{}])
    link = (
        "<https://api.github.com/example?per_page=1&page="
        f"{count}>; rel=\"last\""
    )
    return response(data=[{}], headers={"Link": link})


class GitHubCommitTests(unittest.IsolatedAsyncioTestCase):
    async def test_24_hour_window_is_paginated_and_filters_both_boundaries(self):
        end = datetime(2026, 8, 18, 8, tzinfo=timezone.utc)
        start = end - timedelta(hours=24)
        first_page = [commit_at(end - timedelta(hours=1), index) for index in range(100)]
        second_page = [
            commit_at(start, 100),
            commit_at(start - timedelta(seconds=1), 101),
            commit_at(end, 102),
            commit_at(end + timedelta(seconds=1), 103),
        ]
        request = AsyncMock(
            side_effect=[
                response(data=metadata()),
                response(data=first_page),
                response(data=second_page),
            ]
        )

        with patch("github.client._request_json", request):
            result = await client._fetch_repo_commits_between_with_session(
                object(),
                "Owner/Repo",
                start,
                end,
            )

        self.assertEqual(result["count"], 102)
        self.assertEqual(len(result["commits"]), 102)
        self.assertIn("change\\_100", result["commits"][-2]["msg"])
        self.assertIn("A\\_\\[uthor\\]", result["commits"][-2]["author"])
        page_calls = request.await_args_list[1:]
        self.assertEqual(page_calls[0].kwargs["params"]["page"], 1)
        self.assertEqual(page_calls[1].kwargs["params"]["page"], 2)
        self.assertIn("since", page_calls[0].kwargs["params"])
        self.assertIn("until", page_calls[0].kwargs["params"])

    async def test_failed_later_page_discards_partial_commit_count(self):
        end = datetime(2026, 8, 18, 8, tzinfo=timezone.utc)
        start = end - timedelta(hours=24)
        first_page = [commit_at(end - timedelta(hours=1), index) for index in range(100)]
        request = AsyncMock(
            side_effect=[
                response(data=metadata()),
                response(data=first_page),
                response(status=429),
            ]
        )

        with patch("github.client._request_json", request):
            result = await client._fetch_repo_commits_between_with_session(
                object(),
                "Owner/Repo",
                start,
                end,
            )

        self.assertIsNone(result)

    async def test_private_repository_is_rejected_before_commit_request(self):
        request = AsyncMock(
            return_value=response(
                data=metadata(private=True, visibility="private")
            )
        )
        end = datetime(2026, 8, 18, 8, tzinfo=timezone.utc)

        with patch("github.client._request_json", request):
            result = await client._fetch_repo_commits_between_with_session(
                object(),
                "Owner/Private",
                end - timedelta(hours=24),
                end,
            )

        self.assertIsNone(result)
        self.assertEqual(request.await_count, 1)

    async def test_empty_public_repo_409_is_a_complete_zero_commit_window(self):
        end = datetime(2026, 8, 18, 8, tzinfo=timezone.utc)
        start = end - timedelta(hours=24)
        request = AsyncMock(
            side_effect=[
                response(data=metadata()),
                response(
                    status=409,
                    data={"message": "Git Repository is empty."},
                ),
            ]
        )

        with patch("github.client._request_json", request):
            result = await client._fetch_repo_commits_between_with_session(
                object(),
                "Owner/Repo",
                start,
                end,
            )

        self.assertEqual(result["repo_path"], "Owner/Repo")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["commits"], [])
        self.assertEqual(request.await_count, 2)

    async def test_unrecognized_commit_409_remains_incomplete(self):
        end = datetime(2026, 8, 18, 8, tzinfo=timezone.utc)
        request = AsyncMock(
            side_effect=[
                response(data=metadata()),
                response(status=409, data={"message": "Conflict"}),
            ]
        )

        with patch("github.client._request_json", request):
            result = await client._fetch_repo_commits_between_with_session(
                object(),
                "Owner/Repo",
                end - timedelta(hours=24),
                end,
            )

        self.assertIsNone(result)

    async def test_weekly_empty_repo_409_returns_zero_but_other_409_fails(self):
        for message, expected_count in (
            ("Git Repository is empty.", 0),
            ("Conflict", None),
        ):
            with self.subTest(message=message):
                request = AsyncMock(
                    side_effect=[
                        response(data=metadata()),
                        response(status=409, data={"message": message}),
                    ]
                )
                with (
                    patch(
                        "github.client._make_session",
                        return_value=FakeSessionContext(),
                    ),
                    patch("github.client._request_json", request),
                ):
                    result = await client.fetch_repo_weekly_commits(
                        "Owner/Repo"
                    )

                if expected_count is None:
                    self.assertIsNone(result)
                else:
                    self.assertEqual(result["count"], expected_count)
                    self.assertEqual(result["commits"], [])


class GitHubOverviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_overview_uses_subscriber_count_and_excludes_prs_from_issues(self):
        request = AsyncMock(
            side_effect=[
                response(data=metadata()),
                one_item_count(3),
                one_item_count(5),
                one_item_count(10),
                one_item_count(12),
            ]
        )

        with (
            patch("github.client._make_session", return_value=FakeSessionContext()),
            patch("github.client._request_json", request),
        ):
            result = await client.fetch_repo_overview("Owner/Repo")

        self.assertEqual(result["stars"], 11)
        self.assertEqual(result["forks"], 4)
        self.assertEqual(result["subscribers"], 3)
        self.assertEqual(result["open_prs"], 3)
        self.assertEqual(result["closed_prs"], 5)
        self.assertEqual(result["open_issues"], 7)
        self.assertEqual(result["closed_issues"], 7)
        self.assertEqual(request.await_count, 5)

    async def test_disabled_issues_are_explicit_and_skip_issue_endpoints(self):
        request = AsyncMock(
            side_effect=[
                response(data=metadata(has_issues=False)),
                one_item_count(1),
                one_item_count(2),
            ]
        )

        with (
            patch("github.client._make_session", return_value=FakeSessionContext()),
            patch("github.client._request_json", request),
        ):
            result = await client.fetch_repo_overview("Owner/Repo")

        self.assertFalse(result["issues_enabled"])
        self.assertIsNone(result["open_issues"])
        self.assertIsNone(result["closed_issues"])
        self.assertEqual(request.await_count, 3)

    async def test_any_count_failure_makes_refresh_incomplete(self):
        request = AsyncMock(
            side_effect=[
                response(data=metadata()),
                response(status=403),
                one_item_count(5),
            ]
        )

        with (
            patch("github.client._make_session", return_value=FakeSessionContext()),
            patch("github.client._request_json", request),
        ):
            result = await client.fetch_repo_overview("Owner/Repo")

        self.assertIsNone(result)

    async def test_nonexistent_and_private_metadata_are_unavailable(self):
        for metadata_response in (
            response(status=404),
            response(data=metadata(private=True, visibility="private")),
        ):
            with self.subTest(status=metadata_response.status):
                request = AsyncMock(return_value=metadata_response)
                with (
                    patch(
                        "github.client._make_session",
                        return_value=FakeSessionContext(),
                    ),
                    patch("github.client._request_json", request),
                ):
                    result = await client.fetch_repo_overview("Owner/Repo")
                self.assertIsNone(result)
                self.assertEqual(request.await_count, 1)


class GitHubAccessTests(unittest.IsolatedAsyncioTestCase):
    def test_optional_credential_header_is_added_only_when_configured(self):
        with patch.object(client, "GITHUB_TOKEN", ""):
            self.assertNotIn("Authorization", client._github_headers())
        with patch.object(client, "GITHUB_TOKEN", "unit-test-credential"):
            self.assertEqual(
                client._github_headers()["Authorization"],
                "Bearer unit-test-credential",
            )

    async def test_rate_limit_creates_circuit_breaker_without_credential_logs(self):
        for status in (403, 429):
            with self.subTest(status=status):
                fake_response = FakeHttpResponse(
                    status,
                    {"message": "rate limited"},
                    {"Retry-After": "60"},
                )
                session = FakeNetworkSession(fake_response)

                with (
                    patch.object(client, "GITHUB_TOKEN", "unit-test-credential"),
                    patch.object(client, "_rate_limited_until", 0.0),
                    patch("github.client.time.time", return_value=1_000.0),
                    self.assertLogs(level="WARNING") as captured,
                ):
                    first = await client._request_json(
                        session,
                        "/repos/Owner/Repo",
                    )
                    second = await client._request_json(
                        session,
                        "/repos/Other/Repo",
                    )

                self.assertEqual(first.status, status)
                self.assertEqual(second.status, 429)
                self.assertEqual(len(session.calls), 1)
                self.assertNotIn(
                    "unit-test-credential",
                    "\n".join(captured.output),
                )


if __name__ == "__main__":
    unittest.main()
