import React from 'react';
import { useParams, Link } from 'react-router-dom';
import MeetingMonitor from './MeetingMonitor';
import SpecViewer from './SpecViewer';

const MeetingPage: React.FC = () => {
    const { meetingId } = useParams<{ meetingId: string }>();
    const id = parseInt(meetingId || "0", 10);

    if (!id) return <div>Invalid ID</div>;

    return (
        <div className="container-fluid h-100 d-flex flex-column px-4 py-3">
            <Link to="/" className="btn btn-link text-decoration-none ps-0 mb-2 align-self-start">
                &larr; Back to Dashboard
            </Link>
            <div className="row g-4 flex-grow-1" style={{ minHeight: 0 }}>
                <div className="col-lg-6 h-100 d-flex flex-column">
                    <MeetingMonitor meetingId={id} />
                </div>
                <div className="col-lg-6 h-100 d-flex flex-column">
                    <SpecViewer meetingId={id} />
                </div>
            </div>
        </div>
    );
};

export default MeetingPage;