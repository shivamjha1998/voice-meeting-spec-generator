def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_project(client):
    response = client.post(
        "/projects/",
        json={
            "name": "Test Project",
            "description": "A unit test project",
            "github_repo_url": "https://github.com/test/repo"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Project"
    assert "id" in data

def test_read_projects(client):
    # Create a project first
    client.post(
        "/projects/",
        json={"name": "Project A", "description": "Desc A"}
    )
    client.post(
        "/projects/",
        json={"name": "Project B", "description": "Desc B"}
    )

    response = client.get("/projects/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Project A"

def test_get_project_by_id(client):
    # Create project
    create_res = client.post(
        "/projects/",
        json={"name": "Single Project", "description": "For ID lookup"}
    )
    project_id = create_res.json()["id"]

    # Fetch it
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Single Project"

def test_delete_project(client):
    # Create project
    create_res = client.post(
        "/projects/",
        json={"name": "Delete Me"}
    )
    project_id = create_res.json()["id"]

    # Delete it
    del_res = client.delete(f"/projects/{project_id}")
    assert del_res.status_code == 200
    
    # Verify it's gone
    get_res = client.get(f"/projects/{project_id}")
    assert get_res.status_code == 404