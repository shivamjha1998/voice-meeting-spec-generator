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
                onSelectMeeting(meeting.id); // Go to meeting view immediately
            }
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="p-6">
            <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

            {/* Create Project Bar */}
            <div className="mb-8 bg-white p-4 rounded shadow flex flex-col gap-4">
                <h3 className="font-semibold text-gray-700">Create New Project</h3>
                <div className="flex gap-4">
                    <input
                        type="text"
                        placeholder="Project Name"
                        className="border p-2 rounded flex-1"
                        value={newProjectName}
                        onChange={e => setNewProjectName(e.target.value)}
                    />

                    {/* Repository Dropdown */}
                    <select
                        className="border p-2 rounded flex-1"
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

                    <button
                        onClick={handleCreateProject}
                        disabled={loading}
                        className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                    >
                        {loading ? "Creating..." : "Create"}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {projects.map(project => (
                    <div key={project.id} className="border p-6 rounded shadow bg-white flex flex-col justify-between">
                        <div>
                            <h3 className="text-xl font-bold mb-1">{project.name}</h3>
                            <p className="text-gray-500 text-sm mb-4">{project.description}</p>

                            <h4 className="font-semibold text-gray-700 mb-2 border-b pb-1">Recent Meetings</h4>
                            <ul className="space-y-2 mb-4 max-h-40 overflow-y-auto">
                                {project.meetings && project.meetings.length > 0 ? (
                                    project.meetings.map(m => (
                                        <li key={m.id} className="flex justify-between items-center text-sm">
                                            <span>Meeting #{m.id}</span>
                                            <button
                                                onClick={() => onSelectMeeting(m.id)}
                                                className="text-blue-600 hover:underline"
                                            >
                                                Open
                                            </button>
                                        </li>
                                    ))
                                ) : (
                                    <li className="text-gray-400 text-sm">No meetings yet.</li>
                                )}
                            </ul>
                        </div>
                        <button
                            onClick={() => handleCreateMeeting(project.id)}
                            className="w-full mt-4 bg-green-50 text-green-700 border border-green-200 py-2 rounded hover:bg-green-100 transition"
                        >
                            + Start New Meeting
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Dashboard;