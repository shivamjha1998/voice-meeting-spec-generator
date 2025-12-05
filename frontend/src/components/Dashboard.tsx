import React, { useState, useEffect } from 'react';

interface Project {
    id: number;
    name: string;
    description: string;
}

const Dashboard: React.FC = () => {
    const [projects, setProjects] = useState<Project[]>([]);

    useEffect(() => {
        // Fetch projects from API
        fetch('http://localhost:8000/projects/')
            .then(res => res.json())
            .then(data => setProjects(data))
            .catch(err => console.error("Error fetching projects:", err));
    }, []);

    return (
        <div className="p-6">
            <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

            <div className="mb-8">
                <h2 className="text-xl font-semibold mb-4">Projects</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map(project => (
                        <div key={project.id} className="border p-4 rounded shadow hover:shadow-lg transition">
                            <h3 className="text-lg font-bold">{project.name}</h3>
                            <p className="text-gray-600">{project.description}</p>
                        </div>
                    ))}
                    {projects.length === 0 && (
                        <p className="text-gray-500">No projects found. Create one to get started.</p>
                    )}
                </div>
            </div>

            <div>
                <h2 className="text-xl font-semibold mb-4">Recent Meetings</h2>
                <p className="text-gray-500">No recent meetings.</p>
            </div>
        </div>
    );
};

export default Dashboard;
