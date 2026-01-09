from backend.common import models
from backend.api.main import app
from backend.api.auth import get_current_user

def test_access_control_other_users_project(client, db_session, test_user):
    """Ensure User A cannot access User B's project."""

    # 1. Create a second user (Attacker/Other User)
    other_user = models.User(
        email="other@example.com",
        username="other",
        github_token="dummy"
    )
    db_session.add(other_user)
    db_session.commit()

    # 2. Create a project owned by the PRIMARY test_user (User A)
    project = models.Project(
        name="Secret Project",
        description="Private",
        github_repo_url="http://github.com/a/b",
        owner_id=test_user.id
    )
    db_session.add(project)
    db_session.commit()

    # 3. Switch the API client to act as 'other_user' (User B)
    app.dependency_overrides[get_current_user] = lambda: other_user

    # 4. Attempt to read the project
    response = client.get(f"/projects/{project.id}")

    # 5. Reset override
    app.dependency_overrides[get_current_user] = lambda: test_user

    # Expect 403 Forbidden
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]

def test_delete_other_users_project(client, db_session, test_user):
    """Ensure User A cannot delete User B's project."""

    # 1. Create a project owned by 'other_user'
    other_user = models.User(
        email="victim@example.com",
        username="victim",
        github_token="d"
    )

    db_session.add(other_user)
    db_session.commit()

    project = models.Project(name="Victim Project", owner_id=other_user.id)
    db_session.add(project)
    db_session.commit()

    # 2. Current client is logged in as 'test_user' (Attacker)
    response = client.delete(f"/projects/{project.id}")

    assert response.status_code == 403
