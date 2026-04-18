export default function LoadingSpinner({ text = "Loading..." }) {
  return (
    <div className="loading-center fade-in">
      <div style={{ textAlign: "center" }}>
        <div className="spinner" style={{ margin: "0 auto 1rem" }} />
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>{text}</p>
      </div>
    </div>
  );
}
