import React, { useState, useEffect } from 'react';

interface Specification {
    id: number;
    content: string;
    version: string;
    created_at: string;
}

const SpecViewer: React.FC = () => {
    const [spec, setSpec] = useState<Specification | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const meetingId = 1; // Hardcoded for MVP

    // Function to check if a spec exists
    const fetchSpec = async () => {
        try {
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/specification`);
            if (res.ok) {
                const data = await res.json();
                setSpec(data);
                setIsLoading(false); // Stop loading if found
                return true;
            }
        } catch (err) {
            console.error("Error fetching spec:", err);
        }
        return false;
    };

    // Initial check on load
    useEffect(() => {
        fetchSpec();
    }, []);

    // Polling effect: If loading, check every 3 seconds
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
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/generate`, {
                method: 'POST'
            });

            if (!res.ok) {
                throw new Error("Failed to trigger generation");
            }
            // If successful, the useEffect hook will take over polling
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

    return (
        <div className="border p-4 rounded shadow bg-white mt-6 h-96 flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Specification Viewer</h2>
                {spec && (
                    <span className="text-sm text-gray-500">Version: {spec.version}</span>
                )}
            </div>

            <div className="flex-1 overflow-y-auto bg-gray-50 p-4 rounded border font-mono whitespace-pre-wrap text-sm">
                {isLoading ? (
                    <div className="flex items-center justify-center h-full text-blue-600 animate-pulse">
                        Generating Specification with AI... (this may take a moment)
                    </div>
                ) : error ? (
                    <div className="text-red-500 text-center h-full flex items-center justify-center">
                        {error}
                    </div>
                ) : spec ? (
                    spec.content
                ) : (
                    <div className="text-gray-400 text-center h-full flex items-center justify-center">
                        No specification generated yet.
                    </div>
                )}
            </div>

            <div className="mt-4 flex gap-2">
                <button
                    onClick={handleGenerate}
                    disabled={isLoading}
                    className={`px-4 py-2 rounded text-white transition ${isLoading ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"
                        }`}
                >
                    {spec ? "Regenerate Spec" : "Generate Spec"}
                </button>

                {spec && (
                    <>
                        <button
                            onClick={handleExport}
                            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded transition"
                        >
                            Export Markdown
                        </button>
                        <button className="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded transition">
                            Create GitHub Issues
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};

export default SpecViewer;
