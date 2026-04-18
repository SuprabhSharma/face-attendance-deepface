import { useEffect, useState } from "react";
import {
  getGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  getGroupStudents,
  addStudentToGroup,
  removeStudentFromGroup,
} from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";

export default function GroupManagement() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState(null);

  // Active group detail panel
  const [activeGroup, setActiveGroup] = useState(null);
  const [students, setStudents] = useState([]);
  const [studentEmail, setStudentEmail] = useState("");
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [editName, setEditName] = useState("");
  const [editing, setEditing] = useState(false);

  const fetchGroups = () => {
    getGroups()
      .then((res) => setGroups(res.groups || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchGroups(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setMsg(null);
    try {
      await createGroup(newName.trim());
      setNewName("");
      fetchGroups();
      setMsg({ type: "success", text: "Group created." });
    } catch (err) {
      setMsg({ type: "error", text: err.message });
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this group and all its data?")) return;
    try {
      await deleteGroup(id);
      if (activeGroup?.id === id) {
        setActiveGroup(null);
        setStudents([]);
      }
      fetchGroups();
      setMsg({ type: "success", text: "Group deleted." });
    } catch (err) {
      setMsg({ type: "error", text: err.message });
    }
  };

  const openGroup = async (group) => {
    setActiveGroup(group);
    setEditName(group.name);
    setEditing(false);
    setLoadingStudents(true);
    try {
      const res = await getGroupStudents(group.id);
      setStudents(res.students || []);
    } catch {
      setStudents([]);
    } finally {
      setLoadingStudents(false);
    }
  };

  const handleRename = async () => {
    if (!editName.trim() || editName.trim() === activeGroup.name) {
      setEditing(false);
      return;
    }
    try {
      const res = await updateGroup(activeGroup.id, editName.trim());
      setActiveGroup(res.group);
      setEditing(false);
      fetchGroups();
    } catch (err) {
      setMsg({ type: "error", text: err.message });
    }
  };

  const handleAddStudent = async (e) => {
    e.preventDefault();
    if (!studentEmail.trim()) return;
    setMsg(null);
    try {
      await addStudentToGroup(activeGroup.id, studentEmail.trim());
      setStudentEmail("");
      const res = await getGroupStudents(activeGroup.id);
      setStudents(res.students || []);
      fetchGroups();
      setMsg({ type: "success", text: "Student added." });
    } catch (err) {
      setMsg({ type: "error", text: err.message });
    }
  };

  const handleRemoveStudent = async (studentId) => {
    try {
      await removeStudentFromGroup(activeGroup.id, studentId);
      setStudents((prev) => prev.filter((s) => s.student_id !== studentId));
      fetchGroups();
    } catch (err) {
      setMsg({ type: "error", text: err.message });
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>Group Management</h1>
        <p>Create groups and manage student enrolments</p>
      </div>

      {msg && (
        <div className={`alert alert-${msg.type}`} style={{ marginBottom: "1rem" }}>
          {msg.text}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: activeGroup ? "1fr 1fr" : "1fr", gap: "1.5rem" }}>
        {/* Left — Groups list */}
        <div>
          {/* Create form */}
          <form onSubmit={handleCreate} style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem" }}>
            <input
              className="form-input"
              placeholder="New group name…"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" disabled={creating} type="submit">
              {creating ? "…" : "Create"}
            </button>
          </form>

          {groups.length === 0 ? (
            <div className="empty-state">
              <p>No groups yet. Create your first group above.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {groups.map((g) => (
                <div
                  key={g.id}
                  onClick={() => openGroup(g)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "0.85rem 1rem",
                    background: activeGroup?.id === g.id ? "var(--accent-subtle)" : "var(--bg-card)",
                    border: `1px solid ${activeGroup?.id === g.id ? "var(--accent)" : "var(--border)"}`,
                    borderRadius: "var(--radius-md)",
                    cursor: "pointer",
                    transition: "all var(--transition-fast)",
                  }}
                >
                  <div>
                    <strong>{g.name}</strong>
                    <span style={{ marginLeft: "0.75rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {g.student_count} student{g.student_count !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={(e) => { e.stopPropagation(); handleDelete(g.id); }}
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right — Group detail */}
        {activeGroup && (
          <div className="card">
            <div className="card-header">
              {editing ? (
                <div style={{ display: "flex", gap: "0.5rem", flex: 1 }}>
                  <input
                    className="form-input"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleRename()}
                    autoFocus
                    style={{ flex: 1 }}
                  />
                  <button className="btn btn-primary btn-sm" onClick={handleRename}>Save</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => setEditing(false)}>Cancel</button>
                </div>
              ) : (
                <>
                  <h2>{activeGroup.name}</h2>
                  <button className="btn btn-secondary btn-sm" onClick={() => setEditing(true)}>Rename</button>
                </>
              )}
            </div>

            {/* Add student */}
            <form onSubmit={handleAddStudent} style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}>
              <input
                className="form-input"
                type="email"
                placeholder="Student email…"
                value={studentEmail}
                onChange={(e) => setStudentEmail(e.target.value)}
                style={{ flex: 1 }}
              />
              <button className="btn btn-primary btn-sm" type="submit">Add</button>
            </form>

            {/* Students list */}
            {loadingStudents ? (
              <LoadingSpinner text="Loading students…" />
            ) : students.length === 0 ? (
              <div className="empty-state">
                <p>No students in this group yet.</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {students.map((s) => (
                  <div
                    key={s.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "0.65rem 0.85rem",
                      background: "var(--bg-secondary)",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div>
                      <strong style={{ fontSize: "0.875rem" }}>{s.student_name}</strong>
                      <span style={{ marginLeft: "0.5rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                        {s.student_email}
                      </span>
                    </div>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleRemoveStudent(s.student_id)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
