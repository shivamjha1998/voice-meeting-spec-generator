import React from 'react';
import Dashboard from './components/Dashboard';
import MeetingMonitor from './components/MeetingMonitor';
import SpecViewer from './components/SpecViewer';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow p-4">
        <div className="container mx-auto">
          <h1 className="text-xl font-bold text-blue-600">Voice Meeting Spec Generator</h1>
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
