import React from 'react';
import { Card, Button, Form, Badge, ListGroup } from 'react-bootstrap';

export interface Task {
    title: string;
    description: string;
}

export interface SyncResult {
    title: string;
    status: string;
    issue_url: string | null;
    error?: string;
}

interface Props {
    tasks: Task[];
    syncResult: SyncResult[] | null;
    isSyncing: boolean;
    onSync: () => void;
    onDelete: (index: number) => void;
    onChange: (index: number, field: keyof Task, value: string) => void;
    onClose: () => void;
}

const TaskReview: React.FC<Props> = ({
    tasks,
    syncResult,
    isSyncing,
    onSync,
    onDelete,
    onChange,
    onClose
}) => {
    if (tasks.length === 0 && !syncResult) return null;

    return (
        <Card className="shadow-sm border-0 d-flex flex-column overflow-hidden h-100">
            <Card.Header className="bg-light border-bottom py-2 px-3 d-flex justify-content-between align-items-center">
                <h6 className="mb-0 fw-bold text-success">
                    {syncResult ? "📊 Sync Results" : "✅ Task Review"}
                </h6>
                <Button variant="link" size="sm" className="text-muted text-decoration-none p-0" onClick={onClose}>✕</Button>
            </Card.Header>

            <Card.Body className="overflow-auto p-3">
                {syncResult ? (
                    <ListGroup variant="flush">
                        {syncResult.map((r, idx) => (
                            <ListGroup.Item key={idx} className="d-flex justify-content-between align-items-center px-0">
                                <div style={{ maxWidth: '70%' }}>
                                    <span className="fw-bold d-block text-truncate">{r.title}</span>
                                    {r.error && <small className="text-danger">{r.error}</small>}
                                </div>
                                <div>
                                    {r.status === "created" ? (
                                        <a
                                            href={r.issue_url || "#"}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="btn btn-sm btn-outline-success"
                                        >
                                            View Issue ↗
                                        </a>
                                    ) : (
                                        <Badge bg="danger">Failed</Badge>
                                    )}
                                </div>
                            </ListGroup.Item>
                        ))}
                    </ListGroup>
                ) : (
                    <div className="d-flex flex-wrap gap-3">
                        {tasks.map((task, idx) => (
                            <Card key={idx} className="border bg-light flex-grow-1" style={{ minWidth: '300px' }}>
                                <Card.Body className="p-2 d-flex gap-3 align-items-start">
                                    <div className="flex-grow-1">
                                        <Form.Control
                                            type="text"
                                            value={task.title}
                                            onChange={(e) => onChange(idx, 'title', e.target.value)}
                                            className="mb-2 fw-bold form-control-sm border-0 bg-transparent px-0 shadow-none"
                                            placeholder="Task Title"
                                        />
                                        <Form.Control
                                            as="textarea"
                                            rows={2}
                                            value={task.description}
                                            onChange={(e) => onChange(idx, 'description', e.target.value)}
                                            className="form-control-sm"
                                            placeholder="Description..."
                                        />
                                    </div>
                                    <Button variant="link" className="text-muted p-0" onClick={() => onDelete(idx)}>✕</Button>
                                </Card.Body>
                            </Card>
                        ))}
                    </div>
                )}
            </Card.Body>

            {!syncResult && (
                <Card.Footer className="bg-white p-2 text-end">
                    <Button variant="dark" size="sm" onClick={onSync} disabled={isSyncing}>
                        {isSyncing ? "Syncing..." : `Sync ${tasks.length} Issues to GitHub`}
                    </Button>
                </Card.Footer>
            )}
        </Card>
    );
};

export default TaskReview;
