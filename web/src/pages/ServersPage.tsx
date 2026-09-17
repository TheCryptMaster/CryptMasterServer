import { useEffect, useState } from "react";
import { api, ApiError, type PendingEnrollmentOut, type ServerOut } from "../api/client";

export function ServersPage() {
  const [servers, setServers] = useState<ServerOut[] | null>(null);
  const [pending, setPending] = useState<PendingEnrollmentOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  async function load() {
    try {
      const [s, p] = await Promise.all([
        api.get<ServerOut[]>("/api/servers"),
        api.get<PendingEnrollmentOut[]>("/api/servers/pending"),
      ]);
      setServers(s);
      setPending(p);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load servers");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function approve(id: number) {
    await api.post(`/api/servers/pending/${id}/approve`);
    void load();
  }

  async function reject(id: number) {
    await api.post(`/api/servers/pending/${id}/reject`);
    void load();
  }

  async function disable(id: number) {
    if (!confirm("Disable this server? It will no longer be able to fetch secrets.")) return;
    await api.del(`/api/servers/${id}`);
    void load();
  }

  async function addIp(serverId: number) {
    const ip = prompt("New IP address to allow for this server:");
    if (!ip) return;
    await api.post(`/api/servers/${serverId}/ips`, { ip_address: ip });
    void load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>App servers</h1>
        <button className="primary" onClick={() => setShowAdd(true)}>
          Add server manually
        </button>
      </div>
      {error && <p className="field-error">{error}</p>}

      {pending && pending.length > 0 && (
        <section>
          <h2>Pending enrollment requests</h2>
          <table>
            <thead>
              <tr>
                <th>System ID</th>
                <th>Requesting IP</th>
                <th>Requested</th>
                <th>Attempts</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pending.map((p) => (
                <tr key={p.id}>
                  <td className="mono">{p.system_id}</td>
                  <td className="mono">{p.ip_address}</td>
                  <td>{new Date(p.requested_at).toLocaleString()}</td>
                  <td>{p.attempts}</td>
                  <td>
                    <button className="small" onClick={() => approve(p.id)}>
                      Approve
                    </button>
                    <button className="small danger" onClick={() => reject(p.id)}>
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section>
        <h2>Enrolled servers</h2>
        {servers === null ? (
          <p className="muted">Loading...</p>
        ) : servers.length === 0 ? (
          <p className="muted">No servers enrolled yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Label</th>
                <th>System ID</th>
                <th>Allowed IPs</th>
                <th>Status</th>
                <th>Active until</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {servers.map((s) => (
                <tr key={s.id}>
                  <td>{s.label || <span className="muted">(none)</span>}</td>
                  <td className="mono">{s.system_id}</td>
                  <td className="mono">{s.ip_addresses.join(", ") || <span className="muted">none</span>}</td>
                  <td>{s.is_active ? "active" : "disabled"}</td>
                  <td>{new Date(s.active_until).toLocaleDateString()}</td>
                  <td>
                    <button className="small" onClick={() => addIp(s.id)}>
                      + IP
                    </button>
                    {s.is_active && (
                      <button className="small danger" onClick={() => disable(s.id)}>
                        Disable
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {showAdd && <AddServerModal onClose={() => setShowAdd(false)} onSaved={load} />}
    </div>
  );
}

function AddServerModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [systemId, setSystemId] = useState("");
  const [serverSalt, setServerSalt] = useState("");
  const [label, setLabel] = useState("");
  const [ips, setIps] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/servers", {
        system_id: systemId,
        server_salt: serverSalt,
        label,
        ip_addresses: ips.split(",").map((s) => s.trim()).filter(Boolean),
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Add server manually</h2>
        <p className="muted">Prefer approving a real enrollment request above when possible.</p>
        <form onSubmit={submit}>
          <label>
            Label
            <input value={label} onChange={(e) => setLabel(e.target.value)} />
          </label>
          <label>
            System ID
            <input value={systemId} onChange={(e) => setSystemId(e.target.value)} required />
          </label>
          <label>
            Server salt
            <input value={serverSalt} onChange={(e) => setServerSalt(e.target.value)} required />
          </label>
          <label>
            Allowed IP addresses (comma-separated)
            <input value={ips} onChange={(e) => setIps(e.target.value)} />
          </label>
          {error && <p className="field-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Cancel
            </button>
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Saving..." : "Add server"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
