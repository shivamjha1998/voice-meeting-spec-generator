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
        <div className="card shadow-sm h-100">
            <div className="card-header d-flex justify-content-between align-items-center bg-white">
                <h2 className="h5 mb-0 fw-bold">Live Monitor</h2>
                <div className="d-flex align-items-center">
                    <span className={`badge me-2 ${status === "Connected" ? "bg-success" : "bg-secondary"}`}>
                        {status}
                    </span>
                    <div className="d-flex gap-2">
                        <button
                            className="btn btn-primary"
                            onClick={toggleMonitoring}
                        >
                            Summon Bot
                        </button>
                        <button
                            className="btn btn-danger"
                            onClick={handleEndMeeting}
                        >
                            End Meeting
                        </button>
                    </div>
                </div>
            </div>

            <div className="card-body overflow-auto bg-light p-3" style={{ maxHeight: '600px' }}>
                {transcripts.length === 0 ? (
                    <div className="d-flex justify-content-center align-items-center h-100 text-muted">
                        Waiting for speech...
                    </div>
                ) : (
                    transcripts.map((t, idx) => (
                        <div key={t.id || idx} className="mb-3">
                            <div className="small text-muted mb-1">
                                {new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - <span className="fw-bold text-primary">{t.speaker}</span>
                            </div>
                            <div className="bg-white p-2 rounded border shadow-sm text-dark">
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
