import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import MeetingMonitor from './components/MeetingMonitor';
import SpecViewer from './components/SpecViewer';

function App() {
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    // 1. Check if user_id is in the URL (returning from GitHub Login)
    const params = new URLSearchParams(window.location.search);
    const urlUserId = params.get('user_id');

    if (urlUserId) {
      // Save to storage and state
      localStorage.setItem('voice_spec_user_id', urlUserId);
      setUserId(urlUserId);
      // Clean the URL (remove ?user_id=...)
      window.history.replaceState({}, '', window.location.pathname);
    } else {
      // 2. Check if user is already logged in (from storage)
      const storedUserId = localStorage.getItem('voice_spec_user_id');
      if (storedUserId) {
        setUserId(storedUserId);
      }
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('voice_spec_user_id');
    setUserId(null);
  };

  const handleLogin = () => {
    // Redirect to Backend OAuth endpoint
    window.location.href = "http://localhost:8000/auth/github/login";
  };

  // --- Login Screen ---
  if (!userId) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full bg-white shadow-lg rounded-xl p-8 text-center">
          <h1 className="text-3xl font-bold text-blue-600 mb-4">Voice Spec Generator</h1>
          <p className="text-gray-600 mb-8">
            Automatically generate project specifications from your voice meetings using AI.
          </p>

          <button
            onClick={handleLogin}
            className="w-full bg-gray-900 text-white font-bold py-3 px-4 rounded-lg hover:bg-gray-800 transition flex items-center justify-center gap-2"
          >
            {/* Simple GitHub Icon SVG */}
            <svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor" style={{ marginRight: '10px' }}>
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
            Sign in with GitHub
          </button>
        </div>
      </div>
    );
  }

  // --- Main App Screen ---
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow p-4">
        <div className="container mx-auto flex justify-between items-center">
          <h1 className="text-xl font-bold text-blue-600">Voice Meeting Spec Generator</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">User ID: {userId}</span>
            <button
              onClick={handleLogout}
              className="text-sm text-red-500 hover:text-red-700 font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>
      <main className="container mx-auto mt-8 p-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div>
            <Dashboard />
          </div>
          <div>
            <MeetingMonitor />
            <SpecViewer />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;