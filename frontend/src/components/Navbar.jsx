import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (!user) return null;

  return (
    <header
      style={{
        background: "var(--bg-secondary)",
        borderBottom: "1px solid var(--border)",
        padding: "0.85rem 1.5rem",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      <Link
        to="/"
        style={{
          fontWeight: 700,
          fontSize: "1.1rem",
          color: "var(--text-primary)",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <span style={{ fontSize: "1.3rem" }}>📸</span> FaceAttend
      </Link>

      <nav style={{ display: "flex", gap: "1.25rem", alignItems: "center" }}>
        {user.role === "trainer" && (
          <>
            <Link to="/" style={navLink}>Dashboard</Link>
            <Link to="/groups" style={navLink}>Groups</Link>
            <Link to="/attendance" style={navLink}>Attendance</Link>
          </>
        )}

        {user.role === "student" && (
          <>
            <Link to="/" style={navLink}>Dashboard</Link>
            <Link to="/register-face" style={navLink}>Register Face</Link>
          </>
        )}

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            marginLeft: "0.5rem",
            paddingLeft: "1rem",
            borderLeft: "1px solid var(--border)",
          }}
        >
          <span style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
            {user.name}
          </span>
          <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>
    </header>
  );
}

const navLink = {
  color: "var(--text-secondary)",
  fontSize: "0.875rem",
  fontWeight: 500,
  transition: "color 150ms",
};
