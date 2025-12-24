import { useState, useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useNavigate,
  useLocation,
} from "react-router-dom";
import Dashboard from "./components/Dashboard";
import Settings from "./components/Settings";
import ProjectDetails from "./components/ProjectDetails";
import MeetingPage from "./components/MeetingPage";

// Wrapper component to use hooks like useNavigate inside Router context
function AppContent() {
  const [userId, setUserId] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    const urlUserId = params.get("user_id");
    if (urlUserId) {
      return urlUserId;
    }
    return localStorage.getItem("voice_spec_user_id");
  });
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlUserId = params.get("user_id");

    if (urlUserId) {
      localStorage.setItem("voice_spec_user_id", urlUserId);
      window.history.replaceState({}, "", "/"); // Clear URL param
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("voice_spec_user_id");
    setUserId(null);
    navigate("/"); // Redirect to home/login
  };

  const handleLogin = () => {
    window.location.href = "http://localhost:8000/auth/github/login";
  };

  if (!userId) {
    return (
      <div className="d-flex vh-100 align-items-center justify-content-center bg-light">
        <div
          className="card shadow p-5 text-center"
          style={{ maxWidth: "450px" }}
        >
          <h1 className="text-primary fw-bold mb-3">Voice Spec Gen</h1>
          <p className="text-muted mb-4">
            AI-powered project specifications from your voice meetings.
          </p>
          <button
            onClick={handleLogin}
            className="btn btn-dark w-100 py-2 fw-bold"
          >
            Sign in with GitHub
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="d-flex flex-column vh-100 bg-light">
      <nav className="navbar navbar-expand navbar-white bg-white border-bottom px-4 flex-shrink-0">
        <Link to="/" className="navbar-brand fw-bold text-primary">
          Voice Spec Gen
        </Link>

        <div className="navbar-nav me-auto">
          <Link
            to="/"
            className={`nav-link ${
              location.pathname === "/" ? "active fw-bold" : ""
            }`}
          >
            Dashboard
          </Link>
          <Link
            to="/settings"
            className={`nav-link ${
              location.pathname === "/settings" ? "active fw-bold" : ""
            }`}
          >
            Settings
          </Link>
        </div>

        <div className="d-flex align-items-center gap-3">
          <span className="badge bg-secondary fw-normal px-3 py-2">
            User: {userId}
          </span>
          <button
            onClick={handleLogout}
            className="btn btn-outline-danger btn-sm"
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Main content area - fills remaining space */}
      <main className="flex-grow-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard userId={userId} />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/projects/:projectId" element={<ProjectDetails />} />
          <Route path="/meeting/:meetingId" element={<MeetingPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
