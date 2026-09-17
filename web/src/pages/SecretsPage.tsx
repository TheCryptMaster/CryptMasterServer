import { useEffect, useState } from "react";
import { api, ApiError, type SecretOut, type ServerOut } from "../api/client";

export function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretOut[] | null>(null);
  const [servers, setServers] = useState<ServerOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  async function load() {
    try {
      const [s, srv] = await Promise.all([
        api.get<SecretOut[]>("/api/secrets"),
        api.get<ServerOut[]>("/api/servers"),
      ]);
      setSecrets(s);
      setServers(srv);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load secrets");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function remove(id: number) {
    if (!confirm("Delete this secret? Servers with access to it will lose that access.")) return;
    await api.del(`/api/secrets/${id}`);
    void load();
  }

  async function toggleGrant(secretId: number, serverId: number, currentlyGranted: boolean) {
    await api.post(currentlyGranted ? "/api/secrets/revoke" : "/api/secrets/grant", {
      server_id: serverId,
      secret_id: secretId,
    });
    void load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Secrets</h1>
        <button className="primary" onClick={() => setShowAdd(true)}>
          Add secret
        </button>
      </div>
      <p className="muted">Values are never shown again once stored -- only names and which servers can fetch them.</p>
      {error && <p className="field-error">{error}</p>}

      {secrets === null ? (
        <p className="muted">Loading...</p>
      ) : secrets.length === 0 ? (
        <p className="muted">No secrets stored yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Servers with access</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {secrets.map((secret) => (
              <tr key={secret.id}>
                <td className="mono">{secret.name}</td>
                <td>{secret.is_active ? "active" : "deleted"}</td>
                <td>
                  <div className="tag-list">
                    {servers.map((s) => {
                      const granted = secret.server_ids_with_access.includes(s.id);
                      return (
                        <button
                          key={s.id}
                          className={granted ? "tag tag-on" : "tag"}
                          onClick={() => toggleGrant(secret.id, s.id, granted)}
                          title={granted ? "Click to revoke" : "Click to grant"}
                        >
                          {s.label || s.system_id.slice(0, 8)}
                        </button>
                      );
                    })}
                    {servers.length === 0 && <span className="muted">No servers enrolled</span>}
                  </div>
                </td>
                <td>
                  {secret.is_active && (
                    <button className="small danger" onClick={() => remove(secret.id)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showAdd && <AddSecretModal onClose={() => setShowAdd(false)} onSaved={load} />}
    </div>
  );
}

function AddSecretModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/secrets", { name, value });
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
        <h2>Add secret</h2>
        <form onSubmit={submit}>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Value
            <input type="password" value={value} onChange={(e) => setValue(e.target.value)} required />
          </label>
          {error && <p className="field-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Cancel
            </button>
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Saving..." : "Store secret"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
