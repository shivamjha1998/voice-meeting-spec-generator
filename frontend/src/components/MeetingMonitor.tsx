import React, { useState, useEffect, useRef } from 'react';

interface Transcript {
    id: number;
    meeting_id: number;
    speaker: string;
    text: string;
    timestamp: string;
}

interface Props {
    meetingId: number;
}

const MeetingMonitor: React.FC<Props> = ({ meetingId }) => {
    const [transcripts, setTranscripts] = useState<Transcript[]>([]);
    const [status, setStatus] = useState<string>("Disconnected");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new transcripts arrive
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [transcripts]);

    useEffect(() => {
        // Reset transcripts when switching meetings
        setTranscripts([]);
        setStatus("Disconnected");
    }, [meetingId]);

    useEffect(() => {
        let interval: ReturnType<typeof setInterval> | undefined;
        if (status === "Connected") {
            fetchTranscripts();
            interval = setInterval(fetchTranscripts, 2000);
        }
        return () => { if (interval) clearInterval(interval); };
    }, [status, meetingId]);

    const fetchTranscripts = () => {
        fetch(`http://localhost:8000/meetings/${meetingId}/transcripts`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch");
                return res.json();
            })
            .then(data => setTranscripts(data))
            .catch(err => console.error(err));
    };

    return (
        <div className="border p-4 rounded shadow bg-white h-full flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Meeting Monitor</h2>
                <div>
                    <span className={`px-2 py-1 rounded text-white text-sm mr-2 ${status === "Connected" ? "bg-green-500" : "bg-gray-500"}`}>
                        {status}
                    </span>
                    <button
                        className={`text-white px-3 py-1 rounded text-sm transition ${status === "Connected" ? "bg-red-500 hover:bg-red-600" : "bg-blue-600 hover:bg-blue-700"}`}
                        onClick={() => setStatus(status === "Connected" ? "Disconnected" : "Connected")}
                    >
                        {status === "Connected" ? "Stop Polling" : "Start Monitoring"}
                    </button>
                </div>
            </div>

            <div className="flex-1 h-96 overflow-y-auto border p-4 bg-gray-50 rounded">
                {transcripts.length === 0 ? (
                    <p className="text-gray-400 text-center mt-10">
                        {status === "Connected" ? "Waiting for speech..." : "Connect to see transcripts."}
                    </p>
                ) : (
                    transcripts.map((t) => (
                        <div key={t.id} className="mb-4">
                            <div className="text-xs text-gray-500 mb-1">
                                {new Date(t.timestamp).toLocaleTimeString()} - <span className="font-bold text-blue-600">{t.speaker}</span>
                            </div>
                            <div className="bg-white p-2 rounded border shadow-sm text-gray-800">
                                {t.text}
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>
        </div>
    );
};

export default MeetingMonitor;
