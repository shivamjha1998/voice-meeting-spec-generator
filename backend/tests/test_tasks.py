import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from backend.common import models

def test_preview_tasks_json_parsing(client, db_session, test_user):
    """Test extraction of tasks when LLM returns JSON."""

    # 1. Setup Data
    project = models.Project(name="Task Proj", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()

    meeting = models.Meeting(project_id=project.id, meeting_url="http://test")
    db_session.add(meeting)
    db_session.commit()

    spec = models.Specification(
        meeting_id=meeting.id,
        project_id=project.id,
        content="Spec Content"
    )
    db_session.add(spec)
    db_session.commit()

    # 2. Mock LLM Client to return raw JSON string
    fake_json_response = json.dumps({
        "tasks": [
            {"title": "Fix Login", "description": "Login is broken"}
        ]
    })

    with patch("backend.api.main.LLMClient") as MockLLM:
        mock_instance = MockLLM.return_value
        mock_instance.extract_tasks.return_value = fake_json_response

        # 3. Call Endpoint
        response = client.get(f"/meetings/{meeting.id}/tasks/preview")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Fix Login"

@pytest.mark.asyncio
async def test_sync_tasks_to_github(client, db_session, test_user):
    """Test syncing tasks creates Issues via GitHub API."""

    # 1. Setup Data
    project = models.Project(
        name="GH Sync",
        owner_id=test_user.id,
        github_repo_url="https://github.com/owner/repo"
    )
    db_session.add(project)
    db_session.commit()

    meeting = models.Meeting(project_id=project.id, meeting_url="http://test")
    db_session.add(meeting)
    db_session.commit()

    spec = models.Specification(
        meeting_id=meeting.id,
        project_id=project.id,
        content="Spec"
    )
    db_session.add(spec)
    db_session.commit()

    tasks_payload = [
        {"title": "Task 1", "description": "Desc 1"}
    ]

    # 2. Mock HTTPX (GitHub API Call)
    with patch("backend.api.main.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock successful creation response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"number": 101, "html_url": "http://gh.com/issue/101"}
        mock_client.post.return_value = mock_response

        # 3. Call Endpoint
        response = client.post(
            f"/meetings/{meeting.id}/tasks/sync",
            json=tasks_payload
        )

        assert response.status_code == 200
        data = response.json()
        assert "1/1 Created" in data["summary"]
        assert data["results"][0]["status"] == "created"
        assert data["results"][0]["issue_url"] == "http://gh.com/issue/101"

        # 4. Verify DB was updated
        db_task = db_session.query(models.Task).first()
        assert db_task.github_issue_number == 101
