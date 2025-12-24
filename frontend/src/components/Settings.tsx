import React, { useState, useEffect } from "react";

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
    const res = await fetch("http://localhost:8000/settings/");
    const data = await res.json();
    setSettings(data);
  };

  const handleSave = async (key: string, newValue: string) => {
    const setting = settings.find((s) => s.key === key);
    if (!setting) return;

    setLoading(true);
    try {
      await fetch(`http://localhost:8000/settings/${key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...setting, value: newValue }),
      });
      alert("Saved!");
    } catch {
      alert("Error saving setting");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (key: string, val: string) => {
    setSettings((prev) =>
      prev.map((s) => (s.key === key ? { ...s, value: val } : s))
    );
  };

  return (
    <div className="container mt-4" style={{ maxWidth: "800px" }}>
      <h1 className="h3 fw-bold mb-4">System Settings</h1>

      <div className="d-flex flex-column gap-4">
        {settings.map((s) => (
          <div key={s.key} className="card shadow-sm">
            <div className="card-body">
              <div className="mb-3">
                <h3 className="h6 fw-bold mb-1">
                  {s.key.replace("_", " ").toUpperCase()}
                </h3>
                <p className="text-muted small mb-0">{s.description}</p>
              </div>
              <textarea
                className="form-control font-monospace mb-3"
                style={{ minHeight: "120px", fontSize: "0.9rem" }}
                value={s.value}
                onChange={(e) => handleChange(s.key, e.target.value)}
              />
              <div className="text-end">
                <button
                  onClick={() => handleSave(s.key, s.value)}
                  disabled={loading}
                  className="btn btn-primary fw-bold px-4 shadow-sm"
                >
                  {loading ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Settings;
