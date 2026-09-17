import { useEffect, useState } from "react";
import { api, ApiError, type LogEntryOut } from "../api/client";

export function LogsPage() {
  const [logs, setLogs] = useState<LogEntryOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLogs(await api.get<LogEntryOut[]>("/api/logs?limit=200"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load logs");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Activity log</h1>
        <button onClick={load}>Refresh</button>
      </div>
      {error && <p className="field-error">{error}</p>}
      {logs === null ? (
        <p className="muted">Loading...</p>
      ) : logs.length === 0 ? (
        <p className="muted">Nothing logged yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((entry) => (
              <tr key={entry.id} className={entry.significant ? "row-significant" : undefined}>
                <td className="mono">{new Date(entry.timestamp).toLocaleString()}</td>
                <td>{entry.event_type}</td>
                <td className="mono">{entry.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
