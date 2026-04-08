import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { authApi, type User, type LoginRequest } from "../api/auth";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const res = await authApi.getMe();
      setUser(res.data);
    } catch {
      localStorage.removeItem("access_token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = useCallback(
    async (data: LoginRequest) => {
      const res = await authApi.login(data);
      localStorage.setItem("access_token", res.data.access_token);
      await fetchUser();
      navigate("/dashboard");
    },
    [fetchUser, navigate],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    setUser(null);
    navigate("/login");
  }, [navigate]);

  return { user, loading, login, logout };
}
