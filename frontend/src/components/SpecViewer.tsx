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

    // Task Management State
    const [tasks, setTasks] = useState<Task[]>([]);
    const [isPreviewingTasks, setIsPreviewingTasks] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);
    const [syncResult, setSyncResult] = useState<any[] | null>(null);

    // Check if spec exists
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
        fetchSpec();
    }, [meetingId]);

    // Polling effect
    useEffect(() => {
        if (!isLoading) return;
        const interval = setInterval(async () => {
            const found = await fetchSpec();
            if (found) clearInterval(interval);
        }, 3000);
        return () => clearInterval(interval);
    }, [isLoading]);

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

    const handleExport = () => {
        if (!spec) return;
        const blob = new Blob([spec.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `spec_meeting_${meetingId}.md`;
        a.click();
    };

    // --- NEW: Task Logic ---
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
            setTasks([]); // Clear review list on success
        } catch (e) {
            alert("Sync failed");
        } finally {
            setIsSyncing(false);
        }
    };

    return (
        <div className="flex flex-col gap-6">
            {/* Spec Viewer Card */}
            <div className="border p-4 rounded shadow bg-white h-96 flex flex-col">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">Specification Viewer</h2>
                    {spec && <span className="text-sm text-gray-500">v{spec.version}</span>}
                </div>

                <div className="flex-1 overflow-y-auto bg-gray-50 p-4 rounded border font-mono whitespace-pre-wrap text-sm">
                    {isLoading ? (
                        <div className="text-blue-600 animate-pulse text-center mt-10">Generating Specification...</div>
                    ) : error ? (
                        <div className="text-red-500 text-center">{error}</div>
                    ) : spec ? (
                        spec.content
                    ) : (
                        <div className="text-gray-400 text-center mt-10">No specification generated yet.</div>
                    )}
                </div>

                <div className="mt-4 flex gap-2">
                    <button onClick={handleGenerate} disabled={isLoading} className={`px-4 py-2 rounded text-white transition ${isLoading ? "bg-gray-400" : "bg-blue-600 hover:bg-blue-700"}`}>
                        {spec ? "Regenerate Spec" : "Generate Spec"}
                    </button>
                    {spec && (
                        <>
                            <button onClick={handleExport} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
                                Export MD
                            </button>
                            {tasks.length === 0 && !syncResult && (
                                <button onClick={handlePreviewTasks} disabled={isPreviewingTasks} className="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded">
                                    {isPreviewingTasks ? "Extracting..." : "Review Tasks"}
                                </button>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Task Review Card */}
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
                                            className="w-full border p-1 rounded text-sm h-20"
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
