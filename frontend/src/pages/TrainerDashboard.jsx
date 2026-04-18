import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getGroups } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";

export default function TrainerDashboard() {
  const { user } = useAuth();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getGroups()
      .then((res) => setGroups(res.groups || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>Welcome, {user.name} 👋</h1>
        <p>Manage your groups and take attendance</p>
      </div>

      {/* Quick actions */}
      <div className="grid-3" style={{ marginBottom: "2rem" }}>
        <Link to="/groups" style={{ textDecoration: "none" }}>
          <div className="stat-card" style={{ cursor: "pointer", transition: "border-color var(--transition-base)" }}>
            <div className="stat-value" style={{ color: "var(--accent)" }}>
              {groups.length}
            </div>
            <div className="stat-label">Groups</div>
          </div>
        </Link>

        <Link to="/groups" style={{ textDecoration: "none" }}>
          <div className="stat-card" style={{ cursor: "pointer" }}>
            <div className="stat-value" style={{ color: "var(--success)" }}>
              {groups.reduce((sum, g) => sum + (g.student_count || 0), 0)}
            </div>
            <div className="stat-label">Total Students</div>
          </div>
        </Link>

        <Link to="/attendance" style={{ textDecoration: "none" }}>
          <div className="stat-card" style={{ cursor: "pointer" }}>
            <div className="stat-value">📷</div>
            <div className="stat-label">Take Attendance</div>
          </div>
        </Link>
      </div>

      {/* Groups list */}
      <div className="card">
        <div className="card-header">
          <h2>Your Groups</h2>
          <Link to="/groups" className="btn btn-primary btn-sm">Manage Groups</Link>
        </div>

        {groups.length === 0 ? (
          <div className="empty-state">
            <p>No groups yet. Create one to get started.</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {groups.map((g) => (
              <div
                key={g.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.85rem 1rem",
                  background: "var(--bg-secondary)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                }}
              >
                <div>
                  <strong>{g.name}</strong>
                  <span style={{ marginLeft: "0.75rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {g.student_count} student{g.student_count !== 1 ? "s" : ""}
                  </span>
                </div>
                <Link to="/attendance" className="btn btn-secondary btn-sm">
                  Start Attendance
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
