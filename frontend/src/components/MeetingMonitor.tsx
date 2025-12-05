import React, { useState, useEffect } from 'react';

const MeetingMonitor: React.FC = () => {
    const [transcript, setTranscript] = useState<string[]>([]);
    const [status, setStatus] = useState<string>("Disconnected");

    useEffect(() => {
        // Simulate real-time updates
        const interval = setInterval(() => {
            if (status === "Connected") {
                setTranscript(prev => [...prev, `[${new Date().toLocaleTimeString()}] Speaker: ...simulated speech...`]);
            }
        }, 3000);
        return () => clearInterval(interval);
    }, [status]);

    return (
        <div className="border p-4 rounded shadow bg-white">
            <h2 className="text-xl font-bold mb-4">Meeting Monitor</h2>
            <div className="mb-4">
                <span className={`px-2 py-1 rounded text-white ${status === "Connected" ? "bg-green-500" : "bg-gray-500"}`}>
                    {status}
                </span>
                <button
                    className="ml-4 bg-blue-500 text-white px-3 py-1 rounded"
                    onClick={() => setStatus(status === "Connected" ? "Disconnected" : "Connected")}
                >
                    {status === "Connected" ? "Disconnect" : "Connect"}
                </button>
            </div>
            <div className="h-64 overflow-y-auto border p-2 bg-gray-50">
                {transcript.map((line, i) => (
                    <div key={i} className="mb-2 border-b pb-1">{line}</div>
                ))}
                {transcript.length === 0 && <p className="text-gray-400">No transcript yet.</p>}
            </div>
        </div>
    );
};

export default MeetingMonitor;
