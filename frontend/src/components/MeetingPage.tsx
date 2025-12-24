import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import MeetingMonitor from "./MeetingMonitor";
import SpecViewer from "./SpecViewer";
import TaskReview, { type Task, type SyncResult } from "./TaskReview";

const MeetingPage: React.FC = () => {
  const { meetingId } = useParams<{ meetingId: string }>();
  const id = parseInt(meetingId || "0", 10);

  // Lifted State for Task Review
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isPreviewingTasks, setIsPreviewingTasks] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult[] | null>(null);
  const [isAutoGenerating, setIsAutoGenerating] = useState(false);

  const handleMeetingEnd = () => {
    setIsAutoGenerating(true);
  };

  const handlePreviewTasks = async () => {
    setIsPreviewingTasks(true);
    try {
      const res = await fetch(
        `http://localhost:8000/meetings/${id}/tasks/preview`
      );
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
        // Scroll to bottom ideally, but layout change might make it visible automatically
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

  const handleTaskChange = (
    index: number,
    field: keyof Task,
    value: string
  ) => {
    const newTasks = [...tasks];
    newTasks[index] = { ...newTasks[index], [field]: value };
    setTasks(newTasks);
  };

  const handleSyncToGitHub = async () => {
    if (
      !confirm(
        `Are you sure you want to create ${tasks.length} issues on GitHub?`
      )
    )
      return;
    setIsSyncing(true);
    try {
      const res = await fetch(
        `http://localhost:8000/meetings/${id}/tasks/sync`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(tasks),
        }
      );
      const data = await res.json();
      setSyncResult(data.results);
      setTasks([]);
    } catch {
      alert("Sync failed");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCloseReview = () => {
    setTasks([]);
    setSyncResult(null);
  };

  if (!id) return <div>Invalid ID</div>;

  const isTaskReviewOpen = tasks.length > 0 || syncResult !== null;

  return (
    <div className="container-fluid d-flex flex-column px-4 py-3">
      <Link
        to="/"
        className="btn btn-link text-decoration-none ps-0 mb-2 align-self-start"
      >
        &larr; Back to Dashboard
      </Link>

      {/* Top Section: Monitor & Spec Viewer */}
      <div
        className="row g-4 flex-grow-1 flex-shrink-0"
        style={{ minHeight: "0" }}
      >
        <div
          className="col-lg-6 d-flex flex-column"
          style={{
            maxHeight: "100vh",
          }}
        >
          <MeetingMonitor meetingId={id} onMeetingEnd={handleMeetingEnd} />
        </div>
        <div
          className="col-lg-6 d-flex flex-column"
          style={{
            maxHeight: "100vh",
          }}
        >
          <SpecViewer
            meetingId={id}
            onPreviewTasks={handlePreviewTasks}
            isPreviewingTasks={isPreviewingTasks}
            showReviewButton={!isTaskReviewOpen}
            autoGenerateTrigger={isAutoGenerating}
            onGenerationComplete={() => setIsAutoGenerating(false)}
          />
        </div>
      </div>

      {/* Bottom Section: Task Review */}
      {isTaskReviewOpen && (
        <div className="mt-4 flex-shrink-0" style={{ height: "500px" }}>
          <TaskReview
            tasks={tasks}
            syncResult={syncResult}
            isSyncing={isSyncing}
            onSync={handleSyncToGitHub}
            onDelete={handleDeleteTask}
            onChange={handleTaskChange}
            onClose={handleCloseReview}
          />
        </div>
      )}
    </div>
  );
};

export default MeetingPage;
