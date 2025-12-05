import React from 'react';

const SpecViewer: React.FC = () => {
    const mockSpec = `
# Project Specification
## 1. Overview
This is a generated specification based on the meeting.
## 2. Requirements
- Requirement 1
- Requirement 2
  `;

    return (
        <div className="border p-4 rounded shadow bg-white mt-6">
            <h2 className="text-xl font-bold mb-4">Specification Viewer</h2>
            <div className="bg-gray-50 p-4 rounded font-mono whitespace-pre-wrap">
                {mockSpec}
            </div>
            <div className="mt-4 flex gap-2">
                <button className="bg-green-500 text-white px-4 py-2 rounded">Export PDF</button>
                <button className="bg-blue-500 text-white px-4 py-2 rounded">Create GitHub Issues</button>
            </div>
        </div>
    );
};

export default SpecViewer;
