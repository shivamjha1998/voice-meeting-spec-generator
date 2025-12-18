import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, Button, Form, Badge, Alert, Spinner } from 'react-bootstrap';

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

interface SyncResult {
    title: string;
    status: string;
    issue_url: string;
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
    const [syncResult, setSyncResult] = useState<SyncResult[] | null>(null);

    // Fetch Spec (Wrapped in useCallback as per your code)
    const fetchSpec = React.useCallback(async () => {
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
    }, [meetingId]);

    // Initial Load
    useEffect(() => {
        setSpec(null);
        setError(null);
        setTasks([]);
        setSyncResult(null);
        setIsPreviewingTasks(false);
        setIsEditing(false);
        fetchSpec();
    }, [meetingId, fetchSpec]);

    // Polling effect
    useEffect(() => {
        if (!isLoading || isEditing) return;
        const interval = setInterval(async () => {
            const found = await fetchSpec();
            if (found) clearInterval(interval);
        }, 3000);
        return () => clearInterval(interval);
    }, [isLoading, isEditing, fetchSpec]);

    const handleGenerate = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/generate`, { method: 'POST' });
            if (!res.ok) throw new Error("Failed to trigger generation");
        } catch {
            setError("Failed to start generation. Ensure backend is running.");
            setIsLoading(false);
        }
    };

    // Edit Logic
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

    // Task Logic
    const handlePreviewTasks = async () => {
        setIsPreviewingTasks(true);
        try {
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
        } catch {
            alert("Sync failed");
        } finally {
            setIsSyncing(false);
        }
    };

    return (
        <div className="d-flex flex-column h-100 gap-3">
            {/* Main Spec Card - Uses flex-grow-1 to take available space */}
            <Card className="shadow-sm border-0 flex-grow-1 overflow-hidden d-flex flex-column" style={{ minHeight: 0 }}>
                <Card.Header className="bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
                    <h5 className="mb-0 fw-bold">📄 Specification Viewer</h5>
                    <div className="d-flex align-items-center gap-2">
                        {spec && !isEditing && (
                            <Button variant="outline-secondary" size="sm" onClick={handleEditToggle}>
                                ✏️ Edit
                            </Button>
                        )}
                        {spec && <Badge bg="light" text="dark" className="border">v{spec.version}</Badge>}
                    </div>
                </Card.Header>

                {/* Content Body - Handles scrolling internally */}
                <Card.Body className="p-0 d-flex flex-column flex-grow-1 overflow-hidden position-relative bg-white">
                    {isLoading ? (
                        <div className="h-100 d-flex flex-column align-items-center justify-content-center text-primary gap-3">
                            <Spinner animation="border" />
                            <span className="fw-bold">Generating Specification...</span>
                        </div>
                    ) : error ? (
                        <div className="h-100 d-flex align-items-center justify-content-center text-danger">{error}</div>
                    ) : isEditing ? (
                        <Form.Control
                            as="textarea"
                            className="h-100 border-0 p-4 font-monospace shadow-none resize-none"
                            style={{ fontSize: '0.875rem', minHeight: '60vh' }}
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            placeholder="Write your specification here..."
                        />
                    ) : spec ? (
                        <div className="h-100 overflow-auto p-4">
                            {/* Render Markdown instead of raw text */}
                            <div className="markdown-body">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {spec.content}
                                </ReactMarkdown>
                            </div>
                        </div>
                    ) : (
                        <div className="h-100 d-flex flex-column align-items-center justify-content-center text-muted">
                            <p className="mb-1">No specification generated yet.</p>
                            <small>End the meeting to generate the first draft.</small>
                        </div>
                    )}
                </Card.Body>

                {/* Footer Actions */}
                <Card.Footer className="bg-white border-top p-3">
                    <div className="d-flex gap-2">
                        {isEditing ? (
                            <>
                                <Button variant="primary" size="sm" onClick={handleSaveSpec} disabled={isSaving}>
                                    {isSaving ? "Saving..." : "Save Changes"}
                                </Button>
                                <Button variant="outline-secondary" size="sm" onClick={handleCancelEdit}>
                                    Cancel
                                </Button>
                            </>
                        ) : (
                            <>
                                <Button
                                    variant="primary" size="sm"
                                    onClick={handleGenerate}
                                    disabled={isLoading}
                                >
                                    {spec ? "Regenerate Spec" : "Generate Spec"}
                                </Button>
                                {spec && (
                                    <>
                                        <Button variant="success" size="sm" onClick={handleExport}>
                                            Export MD
                                        </Button>
                                        {tasks.length === 0 && !syncResult && (
                                            <Button variant="dark" size="sm" className="ms-auto" onClick={handlePreviewTasks} disabled={isPreviewingTasks}>
                                                {isPreviewingTasks ? "Extracting..." : "Review Tasks"}
                                            </Button>
                                        )}
                                    </>
                                )}
                            </>
                        )}
                    </div>
                </Card.Footer>
            </Card>

            {/* Task Review Section (Collapsible) */}
            {(tasks.length > 0 || syncResult) && (
                <Card className="shadow-sm border-0 flex-shrink-0 d-flex flex-column overflow-hidden" style={{ height: '300px' }}>
                    <Card.Header className="bg-light border-bottom py-2 px-3 d-flex justify-content-between align-items-center">
                        <h6 className="mb-0 fw-bold text-success">✅ Task Review</h6>
                        <Button variant="link" size="sm" className="text-muted text-decoration-none p-0" onClick={() => { setTasks([]); setSyncResult(null); }}>✕</Button>
                    </Card.Header>

                    <Card.Body className="overflow-auto p-3">
                        {syncResult ? (
                            <Alert variant="success">
                                <Alert.Heading className="h6">Sync Complete!</Alert.Heading>
                                <ul className="mb-0 ps-3 small">
                                    {syncResult.map((r, idx) => (
                                        <li key={idx}>
                                            {r.title}
                                            {r.status === "created" && <a href={r.issue_url} target="_blank" rel="noreferrer" className="ms-2 fw-bold">View Issue</a>}
                                        </li>
                                    ))}
                                </ul>
                            </Alert>
                        ) : (
                            tasks.map((task, idx) => (
                                <Card key={idx} className="mb-2 border bg-light">
                                    <Card.Body className="p-2 d-flex gap-3 align-items-start">
                                        <div className="flex-grow-1">
                                            <Form.Control
                                                type="text"
                                                value={task.title}
                                                onChange={(e) => handleTaskChange(idx, 'title', e.target.value)}
                                                className="mb-2 fw-bold form-control-sm border-0 bg-transparent px-0 shadow-none"
                                                placeholder="Task Title"
                                            />
                                            <Form.Control
                                                as="textarea"
                                                rows={2}
                                                value={task.description}
                                                onChange={(e) => handleTaskChange(idx, 'description', e.target.value)}
                                                className="form-control-sm"
                                                placeholder="Description..."
                                            />
                                        </div>
                                        <Button variant="link" className="text-muted p-0" onClick={() => handleDeleteTask(idx)}>✕</Button>
                                    </Card.Body>
                                </Card>
                            ))
                        )}
                    </Card.Body>

                    {!syncResult && (
                        <Card.Footer className="bg-white p-2 text-end">
                            <Button variant="dark" size="sm" onClick={handleSyncToGitHub} disabled={isSyncing}>
                                {isSyncing ? "Syncing..." : `Sync ${tasks.length} Issues to GitHub`}
                            </Button>
                        </Card.Footer>
                    )}
                </Card>
            )}
        </div>
    );
};

export default SpecViewer;