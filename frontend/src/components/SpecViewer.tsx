import React, { useState, useEffect } from 'react';

interface Specification {
    id: number;
    content: string;
    version: string;
    created_at: string;
}

interface Task {
    title: string;
    description: string;
}

interface Props {
    meetingId: number;
}

const SpecViewer: React.FC<Props> = ({ meetingId }) => {
    const [spec, setSpec] = useState<Specification | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Edit Mode State
    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState("");
    const [isSaving, setIsSaving] = useState(false);

    // Task Management State
    const [tasks, setTasks] = useState<Task[]>([]);
    const [isPreviewingTasks, setIsPreviewingTasks] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);
    const [syncResult, setSyncResult] = useState<any[] | null>(null);

    // Fetch Spec
    const fetchSpec = async () => {
        try {
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/specification`);
            if (res.ok) {
                const data = await res.json();
                setSpec(data);
                setIsLoading(false);
                return true;
            } else {
                setSpec(null);
            }
        } catch (err) {
            console.error(err);
        }
        return false;
    };

    useEffect(() => {
        setSpec(null);
        setError(null);
        setTasks([]);
        setSyncResult(null);
        setIsPreviewingTasks(false);
        setIsEditing(false);
        fetchSpec();
    }, [meetingId]);

    // Polling effect (only if not editing, to avoid overwriting user work)
    useEffect(() => {
        if (!isLoading || isEditing) return; // Don't poll while editing
        const interval = setInterval(async () => {
            const found = await fetchSpec();
            if (found) clearInterval(interval);
        }, 3000);
        return () => clearInterval(interval);
    }, [isLoading, isEditing]);

    const handleGenerate = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/generate`, { method: 'POST' });
            if (!res.ok) throw new Error("Failed to trigger generation");
        } catch (err) {
            setError("Failed to start generation. Ensure backend is running.");
            setIsLoading(false);
        }
    };

    // --- NEW: Edit Logic ---
    const handleEditToggle = () => {
        if (spec) {
            setEditContent(spec.content);
            setIsEditing(true);
        }
    };

    const handleCancelEdit = () => {
        setIsEditing(false);
        setEditContent("");
    };

    const handleSaveSpec = async () => {
        if (!spec) return;
        setIsSaving(true);
        try {
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/specification`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: editContent })
            });

            if (res.ok) {
                const updatedSpec = await res.json();
                setSpec(updatedSpec);
                setIsEditing(false);
            } else {
                alert("Failed to save changes.");
            }
        } catch (e) {
            console.error(e);
            alert("Error saving specification.");
        } finally {
            setIsSaving(false);
        }
    };

    const handleExport = () => {
        if (!spec) return;
        const blob = new Blob([spec.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `spec_meeting_${meetingId}.md`;
        a.click();
    };

    // --- Task Logic (Existing) ---
    const handlePreviewTasks = async () => {
        setIsPreviewingTasks(true);
        try {
            // Note: If user edited spec, backend fetches from DB, so our Save logic ensures
            // tasks are extracted from the LATEST version.
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/tasks/preview`);
            if (res.ok) {
                const data = await res.json();
                setTasks(data);
            } else {
                alert("Failed to load task preview");
            }
        } catch (e) {
            console.error(e);
        } finally {
            setIsPreviewingTasks(false);
        }
    };

    // ... (handleDeleteTask, handleTaskChange, handleSyncToGitHub remain the same) ...
    // Re-implementing them briefly for completeness of this file block
    const handleDeleteTask = (index: number) => {
        const newTasks = [...tasks];
        newTasks.splice(index, 1);
        setTasks(newTasks);
    };

    const handleTaskChange = (index: number, field: keyof Task, value: string) => {
        const newTasks = [...tasks];
        newTasks[index] = { ...newTasks[index], [field]: value };
        setTasks(newTasks);
    };

    const handleSyncToGitHub = async () => {
        if (!confirm(`Are you sure you want to create ${tasks.length} issues on GitHub?`)) return;
        setIsSyncing(true);
        try {
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/tasks/sync`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(tasks)
            });
            const data = await res.json();
            setSyncResult(data.results);
            setTasks([]);
        } catch (e) {
            alert("Sync failed");
        } finally {
            setIsSyncing(false);
        }
    };

    return (
        <div className="d-flex flex-column gap-4">
            {/* Spec Viewer/Editor Card */}
            <div className="card shadow-sm" style={{ minHeight: '600px' }}>
                <div className="card-header d-flex justify-content-between align-items-center bg-white">
                    <h2 className="h5 mb-0 fw-bold">Specification Viewer</h2>
                    <div className="d-flex align-items-center gap-2">
                        {spec && !isEditing && (
                            <button
                                onClick={handleEditToggle}
                                className="btn btn-outline-secondary btn-sm"
                            >
                                ✏️ Edit
                            </button>
                        )}
                        {spec && <span className="badge bg-light text-dark border">v{spec.version}</span>}
                    </div>
                </div>

                <div className="card-body p-0 position-relative d-flex flex-column">
                    {isLoading ? (
                        <div className="d-flex justify-content-center align-items-center flex-grow-1 text-primary">
                            <div className="spinner-border" role="status">
                                <span className="visually-hidden">Loading...</span>
                            </div>
                            <span className="ms-2">Generating Specification...</span>
                        </div>
                    ) : error ? (
                        <div className="d-flex justify-content-center align-items-center flex-grow-1 text-danger">{error}</div>
                    ) : isEditing ? (
                        <textarea
                            className="form-control border-0 h-100 rounded-0 resize-none font-monospace"
                            style={{ minHeight: '500px' }}
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                        />
                    ) : spec ? (
                        <div className="p-4 font-monospace whitespace-pre-wrap flex-grow-1">
                            {spec.content}
                        </div>
                    ) : (
                        <div className="d-flex justify-content-center align-items-center flex-grow-1 text-muted">
                            <p className="mb-0">No specification generated yet.</p>
                        </div>
                    )}
                </div>

                <div className="card-footer bg-white d-flex gap-2">
                    {isEditing ? (
                        <>
                            <button
                                onClick={handleSaveSpec}
                                disabled={isSaving}
                                className="btn btn-primary fw-bold"
                            >
                                {isSaving ? "Saving..." : "Save Changes"}
                            </button>
                            <button
                                onClick={handleCancelEdit}
                                className="btn btn-secondary"
                            >
                                Cancel
                            </button>
                        </>
                    ) : (
                        <>
                            <button onClick={handleGenerate} disabled={isLoading} className={`btn ${isLoading ? "btn-secondary disabled" : "btn-primary"}`}>
                                {spec ? "Regenerate Spec" : "Generate Spec"}
                            </button>
                            {spec && (
                                <>
                                    <button onClick={handleExport} className="btn btn-success">
                                        Export MD
                                    </button>
                                    {tasks.length === 0 && !syncResult && (
                                        <button onClick={handlePreviewTasks} disabled={isPreviewingTasks} className="btn btn-dark">
                                            {isPreviewingTasks ? "Extracting..." : "Review Tasks"}
                                        </button>
                                    )}
                                </>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Task Review Card (Same as before) */}
            {(tasks.length > 0 || syncResult) && (
                <div className="border p-4 rounded shadow bg-white">
                    <h2 className="text-xl font-bold mb-4">Task Review & Sync</h2>

                    {syncResult ? (
                        <div className="bg-green-50 p-4 rounded">
                            <h3 className="font-bold text-green-700 mb-2">Sync Complete!</h3>
                            <ul className="list-disc pl-5 text-sm">
                                {syncResult.map((r: any, idx: number) => (
                                    <li key={idx}>
                                        {r.title} -
                                        {r.status === "created" ? (
                                            <a href={r.issue_url} target="_blank" rel="noreferrer" className="text-blue-600 underline ml-1">View Issue</a>
                                        ) : (
                                            <span className="text-red-500 ml-1">Failed</span>
                                        )}
                                    </li>
                                ))}
                            </ul>
                            <button onClick={() => setSyncResult(null)} className="mt-4 text-sm text-gray-500 hover:underline">Dismiss</button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {tasks.map((task, idx) => (
                                <div key={idx} className="border p-3 rounded bg-gray-50 flex gap-4 items-start">
                                    <div className="flex-1 space-y-2">
                                        <input
                                            className="w-full border p-1 rounded font-semibold"
                                            value={task.title}
                                            onChange={(e) => handleTaskChange(idx, 'title', e.target.value)}
                                        />
                                        <textarea
                                            className="w-full border p-1 rounded text-sm h-32"
                                            value={task.description}
                                            onChange={(e) => handleTaskChange(idx, 'description', e.target.value)}
                                        />
                                    </div>
                                    <button onClick={() => handleDeleteTask(idx)} className="text-red-500 hover:text-red-700 text-xl font-bold">&times;</button>
                                </div>
                            ))}
                            <div className="flex justify-end gap-2 mt-4">
                                <button onClick={() => setTasks([])} className="text-gray-500 px-4 py-2">Cancel</button>
                                <button onClick={handleSyncToGitHub} disabled={isSyncing} className="bg-black text-white px-6 py-2 rounded font-bold hover:bg-gray-800">
                                    {isSyncing ? "Syncing..." : `Sync ${tasks.length} Issues to GitHub`}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default SpecViewer;