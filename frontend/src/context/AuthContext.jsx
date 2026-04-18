import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { login as apiLogin, signup as apiSignup, getMe } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  /* On mount (or token change) — hydrate the user from /me */
  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    getMe()
      .then((res) => setUser(res.user))
      .catch(() => {
        /* token expired / invalid → clear everything */
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const login = useCallback(async (email, password) => {
    const res = await apiLogin(email, password);
    localStorage.setItem("token", res.token);
    setToken(res.token);
    setUser(res.user);
    return res;
  }, []);

  const signup = useCallback(async (name, email, password, role) => {
    const res = await apiSignup(name, email, password, role);
    localStorage.setItem("token", res.token);
    setToken(res.token);
    setUser(res.user);
    return res;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
