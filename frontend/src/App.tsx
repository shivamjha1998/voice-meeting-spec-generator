import { useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useNavigate,
  useLocation,
  Navigate,
  Outlet
} from "react-router-dom";
import Dashboard from "./components/Dashboard";
import Settings from "./components/Settings";
import ProjectDetails from "./components/ProjectDetails";
import MeetingPage from "./components/MeetingPage";
import Login from "./components/Login";
import AuthSuccess from "./components/AuthSuccess";

// Layout for protected routes (Navbar + Content)
const ProtectedLayout = () => {
  const [userId, setUserId] = useState<string | null>(localStorage.getItem("voice_spec_user_id"));
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem("voice_spec_user_id");
    localStorage.removeItem("auth_token");
    setUserId(null);
    navigate("/login");
  };

  // Check auth
  if (!localStorage.getItem("auth_token")) {
    return <Navigate to="/login" replace />;
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
            className={`nav-link ${location.pathname === "/" ? "active fw-bold" : ""
              }`}
          >
            Dashboard
          </Link>
          <Link
            to="/settings"
            className={`nav-link ${location.pathname === "/settings" ? "active fw-bold" : ""
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

      <main className="flex-grow-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/auth/success" element={<AuthSuccess />} />

        {/* Protected Routes */}
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Dashboard userId={localStorage.getItem("voice_spec_user_id") || ""} />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/projects/:projectId" element={<ProjectDetails />} />
          <Route path="/meeting/:meetingId" element={<MeetingPage />} />
        </Route>

        {/* Catch all redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
