import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Card,
  Button,
  Form,
  Row,
  Col,
  Badge,
  Spinner,
  ListGroup,
  Modal,
} from "react-bootstrap";

interface Meeting {
  id: number;
  project_id: number;
  name?: string;
  platform: string;
  started_at: string;
}

interface Repository {
  id: number;
  name: string;
  full_name: string;
  html_url: string;
}

interface Project {
  id: number;
  name: string;
  description: string;
  meetings: Meeting[];
}

interface Props {
  userId: string;
}

const Dashboard: React.FC<Props> = ({ userId }) => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [newProjectName, setNewProjectName] = useState("");
  const [loading, setLoading] = useState(false);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoUrl, setSelectedRepoUrl] = useState("");

  // --- Consent Flow variables ---
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [meetingUrl, setMeetingUrl] = useState("");
  const [meetingName, setMeetingName] = useState("");
  const [consentChecked, setConsentChecked] = useState(false);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [startingMeeting, setStartingMeeting] = useState(false);

  const token = localStorage.getItem("auth_token");

  const refreshProjects = React.useCallback(() => {
    fetch("http://localhost:8000/projects/", {
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    })
      .then((res) => res.json())
      .then((data) => setProjects(data))
      .catch((err) => console.error("Error fetching projects:", err));
  }, [token]);

  useEffect(() => {
    refreshProjects();

    if (userId) {
      fetch("http://localhost:8000/user/repos", {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      })
        .then((res) => {
          if (res.ok) return res.json();
          throw new Error("Failed to fetch repos");
        })
        .then((data) => {
          setRepos(data);
          if (data.length > 0) setSelectedRepoUrl(data[0].html_url);
        })
        .catch((err) => console.error(err));
    }
  }, [userId, refreshProjects, token]);

  const handleOpenMeetingModal = (projectId: number) => {
    setActiveProjectId(projectId);
    setMeetingUrl("");
    setMeetingName("");
    setConsentChecked(false);
    setShowMeetingModal(true);
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    if (!selectedRepoUrl) {
      alert("Please select a GitHub repository first.");
      return;
    }

    setLoading(true);
    try {
      await fetch("http://localhost:8000/projects/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newProjectName,
          description: "Project created via UI",
          github_repo_url: selectedRepoUrl,
        }),
      });
      setNewProjectName("");
      refreshProjects();
    } catch (error) {
      console.error(error);
      alert("Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateMeeting = async () => {
    if (!activeProjectId || !meetingUrl || !consentChecked) return;

    setStartingMeeting(true);

    try {
      const res = await fetch("http://localhost:8000/meetings/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: activeProjectId,
          name: meetingName || `Meeting ${new Date().toLocaleString()}`,
          platform: meetingUrl.includes("google") ? "google_meet" : "zoom",
          meeting_url: meetingUrl,
          consent_verified: consentChecked,
        }),
      });

      if (res.ok) {
        const meeting = await res.json();
        // Auto-join Bot
        await fetch(`http://localhost:8000/meetings/${meeting.id}/join`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        navigate(`/meeting/${meeting.id}`);
      }
    } catch (err) {
      console.error(err);
      alert("Failed to start meeting.");
    } finally {
      setStartingMeeting(false);
      setShowMeetingModal(false);
    }
  };

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="fw-bold mb-0">Dashboard</h2>
        <Badge bg="secondary" className="px-3 py-2">
          Total Projects: {projects.length}
        </Badge>
      </div>

      {/* Create Project Section */}
      <Card className="shadow-sm mb-5 border-0">
        <Card.Body className="p-4">
          <h5 className="fw-bold mb-3">Create New Project</h5>
          <div className="d-flex flex-column flex-md-row gap-3">
            <Form.Control
              type="text"
              placeholder="Project Name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              className="flex-grow-1"
            />
            <Form.Select
              value={selectedRepoUrl}
              onChange={(e) => setSelectedRepoUrl(e.target.value)}
              className="flex-grow-1"
              style={{ maxWidth: "400px" }}
            >
              <option value="" disabled>
                Select GitHub Repository
              </option>
              {repos.map((repo) => (
                <option key={repo.id} value={repo.html_url}>
                  {repo.full_name}
                </option>
              ))}
            </Form.Select>
            <Button
              variant="dark"
              onClick={handleCreateProject}
              disabled={loading || !newProjectName || !selectedRepoUrl}
              style={{ minWidth: "120px" }}
            >
              {loading ? <Spinner animation="border" size="sm" /> : "Create"}
            </Button>
          </div>
        </Card.Body>
      </Card>

      {/* Meeting Start Modal (Consent Flow) */}
      <Modal
        show={showMeetingModal}
        onHide={() => setShowMeetingModal(false)}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title className="fw-bold">Start New Meeting</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3">
            <Form.Label>Meeting Name (Optional)</Form.Label>
            <Form.Control
              type="text"
              placeholder="e.g. Kickoff, Weekly Sync"
              value={meetingName}
              onChange={(e) => setMeetingName(e.target.value)}
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Meeting URL (Zoom or Google Meet)</Form.Label>
            <Form.Control
              type="url"
              placeholder="https://..."
              value={meetingUrl}
              onChange={(e) => setMeetingUrl(e.target.value)}
            />
          </Form.Group>

          <Card className="bg-light border-0 mb-3">
            <Card.Body>
              <Form.Check
                type="checkbox"
                id="consent-checkbox"
                label="I have notified all participants that an AI Bot will join and record this meeting."
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                className="small fw-bold"
              />
              <Form.Text className="text-muted">
                Required for legal compliance and bot participation.
              </Form.Text>
            </Card.Body>
          </Card>
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant="secondary"
            onClick={() => setShowMeetingModal(false)}
          >
            Cancel
          </Button>
          <Button
            variant="success"
            onClick={handleCreateMeeting}
            disabled={!meetingUrl || !consentChecked || startingMeeting}
          >
            {startingMeeting ? <Spinner size="sm" className="me-2" /> : null}
            Start Meeting & Invite Bot
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Projects Grid */}
      <Row xs={1} md={2} lg={3} className="g-4">
        {projects.map((project) => (
          <Col key={project.id}>
            <Card className="h-100 shadow-sm border-0">
              <Card.Body className="d-flex flex-column">
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <h5
                    className="card-title fw-bold text-truncate"
                    title={project.name}
                  >
                    {project.name}
                  </h5>
                  <Badge bg="light" text="dark" className="border">
                    ID: {project.id}
                  </Badge>
                </div>
                <p className="card-text text-muted small mb-3 flex-grow-1">
                  {project.description}
                </p>

                {/* Recent Meetings Preview */}
                <div className="mb-3">
                  <h6
                    className="fw-bold text-uppercase text-muted"
                    style={{ fontSize: "0.75rem" }}
                  >
                    Recent Meetings
                  </h6>
                  <ListGroup
                    variant="flush"
                    className="small"
                    style={{ maxHeight: "200px", overflowY: "auto" }}
                  >
                    {project.meetings && project.meetings.length > 0 ? (
                      project.meetings.map((m) => (
                        <ListGroup.Item
                          key={m.id}
                          className="d-flex justify-content-between align-items-center px-0 py-1 border-0"
                        >
                          <span className="text-truncate" style={{ maxWidth: "150px" }} title={m.name || `Meeting #${m.id}`}>
                            {m.name || `Meeting #${m.id}`}
                          </span>
                          <Link
                            to={`/meeting/${m.id}`}
                            className="text-decoration-none fw-bold"
                          >
                            Open
                          </Link>
                        </ListGroup.Item>
                      ))
                    ) : (
                      <div className="text-muted fst-italic">
                        No meetings yet.
                      </div>
                    )}
                  </ListGroup>
                </div>

                <div className="d-grid gap-2 mt-auto">
                  <Button
                    variant="success"
                    size="sm"
                    onClick={() => handleOpenMeetingModal(project.id)}
                  >
                    + Start New Meeting
                  </Button>
                  <Link
                    to={`/projects/${project.id}`}
                    className="btn btn-outline-primary btn-sm"
                  >
                    View Project Details
                  </Link>
                </div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default Dashboard;
