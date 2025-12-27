import React from "react";

const Login: React.FC = () => {
    const handleLogin = () => {
        // Redirect to Backend Auth
        window.location.href = "http://localhost:8000/auth/github/login";
    };

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
};

export default Login;
