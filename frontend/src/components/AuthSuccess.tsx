import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const AuthSuccess = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    useEffect(() => {
        const token = searchParams.get("token");
        if (token) {
            localStorage.setItem("auth_token", token);

            // Simple JWT decode to get user_id (sub)
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
            navigate("/login");
        }
    }, [navigate, searchParams]);

    return <div>Logging in...</div>;
};
export default AuthSuccess;
