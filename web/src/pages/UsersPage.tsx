import { useEffect, useState } from "react";
import { api, ApiError, type CreateUserResponse, type UserOut } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function UsersPage() {
  const [users, setUsers] = useState<UserOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const { session } = useAuth();
  const isAdmin = session?.role === "admin";

  async function load() {
    try {
      setUsers(await api.get<UserOut[]>("/api/users"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function disable(id: number) {
    if (!confirm("Disable this user? They will no longer be able to log in.")) return;
    await api.post(`/api/users/${id}/disable`);
    void load();
  }

  async function setRole(id: number, role: string) {
    await api.post(`/api/users/${id}/role?role=${role}`);
    void load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Users</h1>
        {isAdmin && (
          <button className="primary" onClick={() => setShowAdd(true)}>
            Add user
          </button>
        )}
      </div>
      {!isAdmin && <p className="muted">Only admins can create users or change roles.</p>}
      {error && <p className="field-error">{error}</p>}

      {users === null ? (
        <p className="muted">Loading...</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Active until</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>
                  {isAdmin ? (
                    <select value={u.role} onChange={(e) => setRole(u.id, e.target.value)}>
                      <option value="admin">admin</option>
                      <option value="operator">operator</option>
                    </select>
                  ) : (
                    u.role
                  )}
                </td>
                <td>
                  {!u.is_active ? "disabled" : u.must_change_password ? "pending first login" : "active"}
                </td>
                <td>{new Date(u.active_until).toLocaleDateString()}</td>
                <td>
                  {isAdmin && u.is_active && (
                    <button className="small danger" onClick={() => disable(u.id)}>
                      Disable
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showAdd && <AddUserModal onClose={() => setShowAdd(false)} onSaved={load} />}
    </div>
  );
}

function AddUserModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("operator");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CreateUserResponse | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<CreateUserResponse>("/api/users", { email, role });
      setResult(res);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <h2>User created</h2>
          <p className="muted">
            Give this temporary password to {email}. On first login they'll be required to set their own password
            and enroll their own authenticator app -- there's nothing further to hand them.
          </p>
          <div className="credentials-box">
            <div>
              <span className="muted">Temporary password</span>
              <code>{result.temporary_password}</code>
            </div>
          </div>
          <div className="modal-actions">
            <button className="primary" onClick={onClose}>
              Done
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Add user</h2>
        <form onSubmit={submit}>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Role
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="operator">operator</option>
              <option value="admin">admin</option>
            </select>
          </label>
          {error && <p className="field-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Cancel
            </button>
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Creating..." : "Create user"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
