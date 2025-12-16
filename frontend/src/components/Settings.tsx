import React, { useState, useEffect } from 'react';

interface Setting {
    key: string;
    value: string;
    description: string;
}

const Settings: React.FC = () => {
    const [settings, setSettings] = useState<Setting[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        const res = await fetch('http://localhost:8000/settings/');
        const data = await res.json();
        setSettings(data);
    };

    const handleSave = async (key: string, newValue: string) => {
        const setting = settings.find(s => s.key === key);
        if (!setting) return;

        setLoading(true);
        try {
            await fetch(`http://localhost:8000/settings/${key}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...setting, value: newValue })
            });
            alert("Saved!");
        } catch (e) {
            alert("Error saving setting");
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (key: string, val: string) => {
        setSettings(prev => prev.map(s => s.key === key ? { ...s, value: val } : s));
    };

    return (
        <div className="max-w-4xl mx-auto mt-8">
            <h1 className="text-2xl font-bold mb-6">System Settings</h1>

            <div className="grid gap-6">
                {settings.map((s) => (
                    <div key={s.key} className="bg-white p-6 rounded shadow border">
                        <div className="mb-2">
                            <h3 className="font-bold text-lg">{s.key.replace("_", " ").toUpperCase()}</h3>
                            <p className="text-gray-500 text-sm">{s.description}</p>
                        </div>
                        <textarea
                            className="w-full border p-2 rounded h-32 font-mono text-sm"
                            value={s.value}
                            onChange={(e) => handleChange(s.key, e.target.value)}
                        />
                        <div className="mt-2 text-right">
                            <button
                                onClick={() => handleSave(s.key, s.value)}
                                disabled={loading}
                                className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800"
                            >
                                Save Changes
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Settings;