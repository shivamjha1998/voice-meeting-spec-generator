import React, { useState, useEffect, useRef } from 'react';

interface Transcript {
    id?: number; // Optional now as live updates might not have ID immediately if we don't return it from publish
    speaker: string;
    text: string;
    timestamp: string | number;
}

interface Props {
    meetingId: number;
    onMeetingEnd?: () => void;
}

const MeetingMonitor: React.FC<Props> = ({ meetingId, onMeetingEnd }) => {
    const [transcripts, setTranscripts] = useState<Transcript[]>([]);
    const [status, setStatus] = useState<string>("Disconnected");
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [transcripts]);

    // Initial Fetch (History) + WebSocket Setup
    useEffect(() => {
        // 1. Fetch History first
        fetch(`http://localhost:8000/meetings/${meetingId}/transcripts`)
            .then(res => res.json())
            .then(data => setTranscripts(data))
            .catch(err => console.error(err));

        // 2. Setup WebSocket
        const wsUrl = `ws://localhost:8000/ws/meetings/${meetingId}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("WS Connected");
            setStatus("Connected");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // The payload matches the python dict: { speaker, text, timestamp, ... }
                const newTranscript: Transcript = {
                    speaker: data.speaker,
                    text: data.text,
                    timestamp: data.timestamp
                };

                setTranscripts(prev => [...prev, newTranscript]);
            } catch (e) {
                console.error("WS Parse Error", e);
            }
        };

        ws.onclose = () => {
            console.log("WS Disconnected");
            if (status === "Connected") setStatus("Disconnected");
        };

        ws.onerror = (err) => {
            console.error("WS Error", err);
            setStatus("Error");
        };

        return () => {
            ws.close();
        };
    }, [meetingId]);

    const toggleMonitoring = () => {
        // This button now mostly just triggers the BOT join, 
        // since monitoring is automatic via WS.
        fetch(`http://localhost:8000/meetings/${meetingId}/join`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                console.log("Bot trigger response:", data);
                alert("Bot requested to join!");
            })
            .catch(err => alert(`Failed to start bot: ${err}`));
    };

    const handleEndMeeting = async () => {
        if (!confirm("Are you sure you want to end the meeting? This will stop the bot and generate the spec.")) return;

        try {
            const res = await fetch(`http://localhost:8000/meetings/${meetingId}/end`, {
                method: 'POST'
            });

            if (res.ok) {
                setStatus("Ended");
                alert("Meeting Ended. Specification generation has started.");
                if (onMeetingEnd) onMeetingEnd();
            } else {
                alert("Failed to end meeting");
            }
        } catch (e) {
            console.error(e);
            alert("Network error ending meeting");
        }
    };

    return (
        <div className="border p-4 rounded shadow bg-white h-full flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Meeting Monitor</h2>
                <div>
                    <span className={`px-2 py-1 rounded text-white text-sm mr-2 ${status === "Connected" ? "bg-green-500" : "bg-gray-500"}`}>
                        {status}
                    </span>
                    <div className="flex gap-2">
                        <button
                            className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                            onClick={toggleMonitoring}
                        >
                            Summon Bot
                        </button>
                        <button
                            className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
                            onClick={handleEndMeeting}
                        >
                            End Meeting
                        </button>
                    </div>
                </div>
            </div>

            <div className="flex-1 h-96 overflow-y-auto border p-4 bg-gray-50 rounded">
                {transcripts.length === 0 ? (
                    <p className="text-gray-400 text-center mt-10">
                        Waiting for speech...
                    </p>
                ) : (
                    transcripts.map((t, idx) => (
                        <div key={t.id || idx} className="mb-4">
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
