import { useEffect, useState } from "react";
import { getGroups, getGroupAttendance } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";

export default function AttendanceReport() {
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState("");
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(false);

  useEffect(() => {
    getGroups()
      .then((res) => {
        setGroups(res.groups || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleGroupChange = async (groupId) => {
    setSelectedGroup(groupId);
    if (!groupId) {
      setRecords([]);
      return;
    }
    setLoadingRecords(true);
    try {
      const res = await getGroupAttendance(groupId);
      setRecords(res.records || []);
    } catch {
      setRecords([]);
    } finally {
      setLoadingRecords(false);
    }
  };

  // Group records by date
  const grouped = records.reduce((acc, r) => {
    const date = new Date(r.timestamp).toLocaleDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(r);
    return acc;
  }, {});

  const sortedDates = Object.keys(grouped).sort((a, b) => new Date(b) - new Date(a));

  if (loading) return <LoadingSpinner />;

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>Attendance Reports</h1>
        <p>View attendance records by group</p>
      </div>

      <div className="card" style={{ maxWidth: "400px", marginBottom: "1.5rem" }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">Select Group</label>
          <select
            className="form-select"
            value={selectedGroup}
            onChange={(e) => handleGroupChange(e.target.value)}
          >
            <option value="">Choose a group…</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
      </div>

      {loadingRecords && <LoadingSpinner text="Loading records…" />}

      {!loadingRecords && selectedGroup && records.length === 0 && (
        <div className="empty-state">
          <p>No attendance records for this group yet.</p>
        </div>
      )}

      {!loadingRecords && sortedDates.length > 0 && (
        <div>
          {sortedDates.map((date) => (
            <div key={date} style={{ marginBottom: "1.5rem" }}>
              <h3 style={{
                marginBottom: "0.75rem",
                paddingBottom: "0.5rem",
                borderBottom: "1px solid var(--border)",
                color: "var(--text-secondary)",
                fontSize: "0.95rem",
              }}>
                {date}
              </h3>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Status</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grouped[date].map((r) => (
                      <tr key={r.id}>
                        <td>{r.student_name}</td>
                        <td>
                          <span className={`badge badge-${r.status}`}>{r.status}</span>
                        </td>
                        <td>{new Date(r.timestamp).toLocaleTimeString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
