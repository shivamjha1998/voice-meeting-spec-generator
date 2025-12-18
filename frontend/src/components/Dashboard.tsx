import React, { useState, useEffect } from 'react';

interface Meeting {
    id: number;
    project_id: number;
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
    onSelectMeeting: (id: number) => void;
}

const Dashboard: React.FC<Props> = ({ userId, onSelectMeeting }) => {
    const [projects, setProjects] = useState<Project[]>([]);
    const [newProjectName, setNewProjectName] = useState("");
    const [loading, setLoading] = useState(false);
    const [repos, setRepos] = useState<Repository[]>([]);
    const [selectedRepoUrl, setSelectedRepoUrl] = useState("");

    const refreshProjects = () => {
        fetch('http://localhost:8000/projects/')
            .then(res => res.json())
            .then(data => setProjects(data))
            .catch(err => console.error("Error fetching projects:", err));
    };

    useEffect(() => {
        refreshProjects();

        if (userId) {
            fetch(`http://localhost:8000/user/repos?user_id=${userId}`)
                .then(res => {
                    if (res.ok) return res.json();
                    throw new Error("Failed to fetch repos");
                })
                .then(data => {
                    setRepos(data);
                    if (data.length > 0) setSelectedRepoUrl(data[0].html_url);
                })
                .catch(err => console.error(err));
        }
    }, [userId]);

    const handleCreateProject = async () => {
        if (!newProjectName.trim()) return;
        if (!selectedRepoUrl) {
            alert("Please select a GitHub repository first.");
            return;
        }

        setLoading(true);
        try {
            await fetch('http://localhost:8000/projects/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newProjectName,
                    description: "Project created via UI",
                    github_repo_url: selectedRepoUrl
                })
            });
            setNewProjectName("");
            refreshProjects();
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateMeeting = async (projectId: number) => {
        const url = prompt("Enter Meeting URL (e.g. https://zoom.us/...):", "https://zoom.us/test");
        if (!url) return;

        try {
            const res = await fetch('http://localhost:8000/meetings/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: projectId,
                    platform: "zoom",
                    meeting_url: url
                })
            });
            if (res.ok) {
                const meeting = await res.json();

                // Auto-join Bot
                try {
                    await fetch(`http://localhost:8000/meetings/${meeting.id}/join`, { method: 'POST' });
                    alert("Meeting created! Bot has been summoned to join.");
                } catch (e) {
                    console.error("Failed to auto-join bot:", e);
                }

                onSelectMeeting(meeting.id);
            }
        } catch (err) {
            console.error(err);
        }
    };
    const [loadingMeeting, setLoadingMeeting] = useState<number | null>(null);

    const handleStartMeeting = async (projectId: number) => {
        setLoadingMeeting(projectId);
        await handleCreateMeeting(projectId);
        setLoadingMeeting(null);
    };

    return (
        <div className="d-flex flex-column gap-4">
            <div className="d-flex justify-content-between align-items-center">
                <h2 className="h4 fw-bold mb-0">Dashboard</h2>
                <div className="text-muted">
                    {projects.length > 0 ? (
                        <span>Total Projects: <span className="fw-bold text-dark">{projects.length}</span></span>
                    ) : (
                        <span>No projects found.</span>
                    )}
                </div>
            </div>

            {/* Create Project Section */}
            <div className="card shadow-sm">
                <div className="card-header bg-white">
                    <h3 className="h5 mb-0 fw-bold">Create New Project</h3>
                </div>
                <div className="card-body">
                    <div className="row g-3">
                        <div className="col-md-5">
                            <input
                                type="text"
                                className="form-control"
                                placeholder="Enter Project Name"
                                value={newProjectName}
                                onChange={(e) => setNewProjectName(e.target.value)}
                            />
                        </div>
                        <div className="col-md-5">
                            <select
                                className="form-select"
                                value={selectedRepoUrl}
                                onChange={e => setSelectedRepoUrl(e.target.value)}
                            >
                                <option value="" disabled>Select GitHub Repository</option>
                                {repos.map(repo => (
                                    <option key={repo.id} value={repo.html_url}>
                                        {repo.full_name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="col-md-2">
                            <button
                                onClick={handleCreateProject}
                                disabled={loading}
                                className="btn btn-primary w-100 fw-bold"
                            >
                                {loading ? "Creating..." : "Create"}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Projects list */}
            <div className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
                {projects.map((project) => (
                    <div key={project.id} className="col">
                        <div className="card h-100 shadow-sm hover-shadow transition-all">
                            <div className="card-body d-flex flex-column">
                                <div className="d-flex justify-content-between align-items-start mb-3">
                                    <h3 className="h5 fw-bold text-primary mb-0 text-truncate" title={project.name}>
                                        {project.name}
                                    </h3>
                                    <span className="badge bg-light text-muted border">ID: {project.id}</span>
                                </div>
                                <p className="text-muted small mb-4 flex-grow-1">
                                    {project.description}
                                </p>

                                <h6 className="fw-bold text-dark border-bottom pb-2 mb-2">Recent Meetings</h6>
                                <ul className="list-group list-group-flush mb-3 flex-grow-1" style={{ maxHeight: '150px', overflowY: 'auto' }}>
                                    {project.meetings && project.meetings.length > 0 ? (
                                        project.meetings.map(m => (
                                            <li key={m.id} className="list-group-item d-flex justify-content-between align-items-center px-0 py-1">
                                                <small>Meeting #{m.id}</small>
                                                <button
                                                    onClick={() => onSelectMeeting(m.id)}
                                                    className="btn btn-link btn-sm p-0 text-decoration-none"
                                                >
                                                    Open
                                                </button>
                                            </li>
                                        ))
                                    ) : (
                                        <li className="list-group-item px-0 text-muted small border-0">No meetings yet.</li>
                                    )}
                                </ul>

                                <div className="d-grid mt-auto">
                                    <button
                                        onClick={() => handleStartMeeting(project.id)}
                                        disabled={loadingMeeting === project.id}
                                        className="btn btn-success fw-bold shadow-sm"
                                    >
                                        {loadingMeeting === project.id ? "Starting..." : "+ Start New Meeting"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Dashboard;