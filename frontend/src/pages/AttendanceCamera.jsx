import { useState, useRef, useEffect } from "react";
import {
  getGroups,
  startAttendanceSession,
  endAttendanceSession,
  recognizeFace,
  getSessionAttendance,
} from "../api/client";
import Camera from "../components/Camera";
import LoadingSpinner from "../components/LoadingSpinner";

export default function AttendanceCamera() {
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState("");
  const [session, setSession] = useState(null);
  const [recognised, setRecognised] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [ending, setEnding] = useState(false);
  const cameraRef = useRef(null);

  useEffect(() => {
    getGroups()
      .then((res) => setGroups(res.groups || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleStart = async () => {
    if (!selectedGroup) return;
    setStatus(null);
    try {
      const res = await startAttendanceSession(Number(selectedGroup));
      setSession(res.session);
      setRecognised([]);
      setStatus({ type: "success", text: "Session started. Begin scanning faces." });
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    }
  };

  const handleScan = async () => {
    if (!cameraRef.current || !session) return;
    const base64 = cameraRef.current.capture();
    if (!base64) return;

    setScanning(true);
    setStatus(null);
    try {
      const res = await recognizeFace(base64, Number(selectedGroup), session.id);
      if (res.found) {
        setStatus({ type: "success", text: res.message });
        setRecognised((prev) => {
          if (prev.find((r) => r.id === res.student_id)) return prev;
          return [...prev, { id: res.student_id, name: res.name }];
        });
      } else {
        setStatus({ type: "error", text: res.message });
      }
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    } finally {
      setScanning(false);
    }
  };

  const handleEnd = async () => {
    if (!session) return;
    setEnding(true);
    try {
      const res = await endAttendanceSession(session.id);
      setStatus({ type: "success", text: res.message });
      setSession(null);
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    } finally {
      setEnding(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>Take Attendance</h1>
        <p>Select a group, start a session, and scan student faces</p>
      </div>

      {status && (
        <div className={`alert alert-${status.type}`}>{status.text}</div>
      )}

      {/* Group selection & session controls */}
      {!session ? (
        <div className="card" style={{ maxWidth: "500px", marginBottom: "1.5rem" }}>
          <div className="form-group">
            <label className="form-label">Select Group</label>
            <select
              className="form-select"
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
            >
              <option value="">Choose a group…</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name} ({g.student_count} students)
                </option>
              ))}
            </select>
          </div>
          <button
            className="btn btn-primary btn-lg"
            style={{ width: "100%" }}
            onClick={handleStart}
            disabled={!selectedGroup}
          >
            Start Attendance Session
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
          {/* Camera */}
          <div>
            <Camera captureRef={cameraRef} />
            <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
              <button
                className="btn btn-primary btn-lg"
                style={{ flex: 1 }}
                onClick={handleScan}
                disabled={scanning}
              >
                {scanning ? "Scanning…" : "📷 Scan Face"}
              </button>
              <button
                className="btn btn-danger"
                onClick={handleEnd}
                disabled={ending}
              >
                {ending ? "Ending…" : "End Session"}
              </button>
            </div>
          </div>

          {/* Recognised list */}
          <div className="card">
            <h3 style={{ marginBottom: "1rem" }}>
              Recognised ({recognised.length})
            </h3>
            {recognised.length === 0 ? (
              <div className="empty-state">
                <p>No faces scanned yet.</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {recognised.map((r) => (
                  <div
                    key={r.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.75rem",
                      padding: "0.65rem 0.85rem",
                      background: "var(--success-bg)",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid rgba(16,185,129,0.2)",
                    }}
                  >
                    <span className="badge badge-present">Present</span>
                    <strong style={{ fontSize: "0.875rem" }}>{r.name}</strong>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
