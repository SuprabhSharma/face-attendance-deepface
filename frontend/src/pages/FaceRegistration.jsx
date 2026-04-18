import { useState, useRef } from "react";
import { uploadFace } from "../api/client";
import Camera from "../components/Camera";

export default function FaceRegistration() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const cameraRef = useRef(null);

  const handleCapture = async () => {
    if (!cameraRef.current) return;
    const base64 = cameraRef.current.capture();
    if (!base64) return;

    setStatus(null);
    setLoading(true);
    try {
      const res = await uploadFace(base64);
      setStatus({ type: "success", text: res.message });
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>Register Your Face</h1>
        <p>Look directly at the camera and click capture. This will be used to mark your attendance.</p>
      </div>

      <div style={{ maxWidth: "640px" }}>
        {status && (
          <div className={`alert alert-${status.type}`}>{status.text}</div>
        )}

        <Camera captureRef={cameraRef} />

        <button
          className="btn btn-primary btn-lg"
          style={{ width: "100%", marginTop: "1rem" }}
          onClick={handleCapture}
          disabled={loading}
        >
          {loading ? "Processing…" : "📸 Capture & Register Face"}
        </button>

        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Tips</h3>
          <ul style={{
            paddingLeft: "1.25rem",
            fontSize: "0.875rem",
            color: "var(--text-secondary)",
            lineHeight: "1.8",
          }}>
            <li>Ensure good lighting on your face</li>
            <li>Look directly at the camera</li>
            <li>Remove glasses or hats if possible</li>
            <li>Keep only one person in the frame</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
