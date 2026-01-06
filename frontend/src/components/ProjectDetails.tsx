import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, Button, ListGroup, Badge, Spinner } from "react-bootstrap";

interface Meeting {
  id: number;
  name?: string;
  platform: string;
  started_at: string;
}

interface Project {
  id: number;
  name: string;
  description: string;
  meetings: Meeting[];
}

const ProjectDetails: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem("auth_token");

  useEffect(() => {
    fetch(`http://localhost:8000/projects/${projectId}`, {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    })
      .then((res) => res.json())
      .then((data) => setProject(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [projectId, token]);

  const handleCreateMeeting = async () => {
    const name = prompt("Enter Meeting Name (Optional, e.g. Kickoff):");
    const url = prompt("Enter Meeting URL (Zoom/Meet):");
    if (!url) return;

    // Simple logic to detect platform
    const platform = url.includes("google") ? "google_meet" : "zoom";

    try {
      const res = await fetch("http://localhost:8000/meetings/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: projectId,
          name: name || `Meeting ${new Date().toLocaleString()}`,
          platform: platform,
          meeting_url: url,
        }),
      });
      if (res.ok) {
        // Refresh project data to show new meeting
        const updatedProject = await fetch(
          `http://localhost:8000/projects/${projectId}`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        }
        ).then((r) => r.json());
        setProject(updatedProject);

        // Trigger auto-join
        const meeting = await res.json();
        fetch(`http://localhost:8000/meetings/${meeting.id}/join`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`
          }
        }).catch(console.error);
      }
    } catch (err) {
      console.error(err);
      alert("Failed to create meeting");
    }
  };

  if (loading)
    return (
      <div className="p-5 text-center">
        <Spinner animation="border" />
      </div>
    );
  if (!project)
    return <div className="p-5 text-center text-danger">Project not found</div>;

  return (
    <div className="container mt-4">
      <Link to="/" className="btn btn-link ps-0 mb-3 text-decoration-none">
        &larr; Back to Dashboard
      </Link>

      <div className="d-flex justify-content-between align-items-start mb-4">
        <div>
          <h1 className="fw-bold display-6">{project.name}</h1>
          <p className="text-muted lead">{project.description}</p>
        </div>
        <Button variant="success" onClick={handleCreateMeeting}>
          + New Meeting
        </Button>
      </div>

      <Card className="shadow-sm">
        <Card.Header className="bg-white fw-bold">Meeting History</Card.Header>
        <ListGroup variant="flush">
          {project.meetings.length === 0 ? (
            <ListGroup.Item className="text-muted fst-italic p-4 text-center">
              No meetings recorded yet. Start one above!
            </ListGroup.Item>
          ) : (
            project.meetings.map((meeting) => (
              <ListGroup.Item
                key={meeting.id}
                className="d-flex justify-content-between align-items-center p-3"
              >
                <div>
                  <div className="d-flex align-items-center gap-2">
                    <h5 className="mb-0">
                      {meeting.name || `Meeting #${meeting.id}`}
                    </h5>
                    <Badge
                      bg={meeting.platform === "zoom" ? "primary" : "warning"}
                    >
                      {meeting.platform}
                    </Badge>
                  </div>
                  <small className="text-muted">
                    {meeting.started_at
                      ? new Date(meeting.started_at).toLocaleString()
                      : "Not started"}
                  </small>
                </div>
                <Link to={`/meeting/${meeting.id}`}>
                  <Button variant="outline-primary" size="sm">
                    Open Workspace &rarr;
                  </Button>
                </Link>
              </ListGroup.Item>
            ))
          )}
        </ListGroup>
      </Card>
    </div>
  );
};

export default ProjectDetails;
