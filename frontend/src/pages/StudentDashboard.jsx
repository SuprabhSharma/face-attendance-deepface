import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { getMyAttendance, getGroups } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import { Link } from "react-router-dom";

export default function StudentDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [records, setRecords] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getMyAttendance(), getGroups()])
      .then(([attRes, grpRes]) => {
        setStats(attRes.stats);
        setRecords(attRes.records || []);
        setGroups(grpRes.groups || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  const percentage = stats && stats.total > 0
    ? Math.round((stats.present / stats.total) * 100)
    : 0;

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>Welcome, {user.name} 👋</h1>
        <p>Your attendance overview</p>
      </div>

      {/* Stats */}
      <div className="grid-3" style={{ marginBottom: "2rem" }}>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--accent)" }}>{stats?.total || 0}</div>
          <div className="stat-label">Total Sessions</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--success)" }}>{stats?.present || 0}</div>
          <div className="stat-label">Present</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--error)" }}>{stats?.absent || 0}</div>
          <div className="stat-label">Absent</div>
        </div>
      </div>

      {/* Attendance percentage bar */}
      {stats && stats.total > 0 && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Attendance Rate</span>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{percentage}%</span>
          </div>
          <div style={{
            width: "100%",
            height: "8px",
            background: "var(--bg-secondary)",
            borderRadius: "9999px",
            overflow: "hidden",
          }}>
            <div style={{
              width: `${percentage}%`,
              height: "100%",
              background: percentage >= 75 ? "var(--success)" : percentage >= 50 ? "var(--warning)" : "var(--error)",
              borderRadius: "9999px",
              transition: "width 0.6s ease",
            }} />
          </div>
        </div>
      )}

      {/* Groups */}
      {groups.length > 0 && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ marginBottom: "1rem" }}>Your Groups</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {groups.map((g) => (
              <span key={g.id} className="badge" style={{
                background: "var(--accent-subtle)",
                color: "var(--accent)",
                padding: "0.35rem 0.85rem",
                fontSize: "0.82rem",
              }}>
                {g.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Face registration prompt */}
      <div className="card" style={{ marginBottom: "1.5rem", borderColor: "rgba(99,102,241,0.2)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3>Face Registration</h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.25rem" }}>
              Register your face so trainers can mark your attendance automatically.
            </p>
          </div>
          <Link to="/register-face" className="btn btn-primary btn-sm">Register Face</Link>
        </div>
      </div>

      {/* Recent records */}
      <div className="card">
        <h3 style={{ marginBottom: "1rem" }}>Recent Attendance</h3>
        {records.length === 0 ? (
          <div className="empty-state">
            <p>No attendance records yet.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Group</th>
                </tr>
              </thead>
              <tbody>
                {records.slice(0, 20).map((r) => (
                  <tr key={r.id}>
                    <td>{new Date(r.timestamp).toLocaleDateString()}</td>
                    <td>
                      <span className={`badge badge-${r.status}`}>{r.status}</span>
                    </td>
                    <td>{r.group_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
