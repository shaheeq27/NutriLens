interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h2>❌ Error</h2>
      <p style={{ color: "red" }}>{message}</p>
      <button
        onClick={onRetry}
        style={{ marginTop: "1rem", padding: "0.5rem 1.5rem", cursor: "pointer" }}
      >
        Try Again
      </button>
    </div>
  );
}
