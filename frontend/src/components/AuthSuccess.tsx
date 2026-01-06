import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const AuthSuccess = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState("Authenticating...");

    useEffect(() => {
        const handleAuth = async () => {
            const code = searchParams.get("code");

            if (code) {
                try {
                    // Exchange the temporary code for a secure token
                    const response = await fetch("http://localhost:8000/auth/exchange", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ code: code }),
                    });

                    if (response.ok) {
                        const data = await response.json();
                        const token = data.access_token;

                        localStorage.setItem("auth_token", token);

                        // Decode to get user_id (sub)
                        try {
                            const base64Url = token.split('.')[1];
                            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                            const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
                                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                            }).join(''));
                            const payload = JSON.parse(jsonPayload);
                            if (payload.sub) {
                                localStorage.setItem("voice_spec_user_id", payload.sub);
                            }
                        } catch (e) {
                            console.error("Failed to decode token", e);
                        }

                        navigate("/");
                    } else {
                        setStatus("Authentication failed. Code expired or invalid.");
                    }
                } catch (err) {
                    console.error("Auth Exchange Error:", err);
                    setStatus("Connection error during authentication.");
                }
            } else {
                // Legacy fallback or error
                const legacyToken = searchParams.get("token");
                if (legacyToken) {
                    // This path is deprecated but kept for safety if backend isn't updated simultaneously
                    localStorage.setItem("auth_token", legacyToken);
                    navigate("/");
                } else {
                    navigate("/login");
                }
            }
        };

        handleAuth();
    }, [navigate, searchParams]);

    return (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '50px' }}>
            <h2>{status}</h2>
        </div>
    );
};
export default AuthSuccess;
