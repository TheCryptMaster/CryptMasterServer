import { useState } from "react";
import { api, ApiError, type DefaultAdminInfo, type MigrateLegacyResponse } from "../api/client";
import { decryptBackup, BackupDecryptionError } from "../crypto/backupFile";

type Mode = "choose" | "create" | "restore" | "migrate";

export function SetupPage() {
  const [mode, setMode] = useState<Mode>("choose");

  if (mode === "choose") {
    return (
      <div className="centered-card">
        <h1>Set up Crypt Master</h1>
        <p className="muted">This server has no vault yet. Choose how to get started.</p>
        <div className="option-list">
          <button className="option-card" onClick={() => setMode("create")}>
            <strong>Create a new vault</strong>
            <span>Start empty, with default admin credentials you'll be required to change immediately.</span>
          </button>
          <button className="option-card" onClick={() => setMode("restore")}>
            <strong>Restore from a backup</strong>
            <span>Upload a Crypt Master backup file and unlock it with its 24-word seed and passphrase.</span>
          </button>
          <button className="option-card" onClick={() => setMode("migrate")}>
            <strong>Migrate from a legacy (v1) server</strong>
            <span>Pull secrets, servers, and users directly from a reachable v1 database.</span>
          </button>
        </div>
      </div>
    );
  }

  if (mode === "create") return <CreateVault onBack={() => setMode("choose")} />;
  if (mode === "restore") return <RestoreVault onBack={() => setMode("choose")} />;
  return <MigrateLegacy onBack={() => setMode("choose")} />;
}

function CreateVault({ onBack }: { onBack: () => void }) {
  const [hostName, setHostName] = useState("secure-api");
  const [domainName, setDomainName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DefaultAdminInfo | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const info = await api.post<DefaultAdminInfo>("/api/setup/create-database", {
        host_name: hostName,
        domain_name: domainName,
      });
      setResult(info);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="centered-card">
        <h1>Vault created</h1>
        <p>{result.note}</p>
        <div className="credentials-box">
          <div>
            <span className="muted">Username</span>
            <code>{result.username}</code>
          </div>
          <div>
            <span className="muted">Password</span>
            <code>{result.password}</code>
          </div>
        </div>
        <button className="primary" onClick={() => { window.location.href = "/login"; }}>
          Continue to login
        </button>
      </div>
    );
  }

  return (
    <div className="centered-card">
      <button className="link-button" onClick={onBack}>
        &larr; Back
      </button>
      <h1>Create a new vault</h1>
      <form onSubmit={submit}>
        <label>
          Host name
          <input value={hostName} onChange={(e) => setHostName(e.target.value)} required />
        </label>
        <label>
          Domain name
          <input
            value={domainName}
            onChange={(e) => setDomainName(e.target.value)}
            placeholder="yourdomain.com"
            required
          />
        </label>
        {error && <p className="field-error">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Creating..." : "Create vault"}
        </button>
      </form>
    </div>
  );
}

function RestoreVault({ onBack }: { onBack: () => void }) {
  const [words, setWords] = useState(Array(24).fill(""));
  const [passphrase, setPassphrase] = useState("");
  const [fileText, setFileText] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setFileText(await file.text());
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!fileText) {
      setError("Choose a backup file first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const data = await decryptBackup(fileText, words, passphrase);
      await api.post("/api/setup/restore-database", { data });
      setDone(true);
    } catch (err) {
      if (err instanceof BackupDecryptionError) setError(err.message);
      else if (err instanceof ApiError) setError(err.message);
      else setError("Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="centered-card">
        <h1>Vault restored</h1>
        <p>Your data has been decrypted locally and loaded into this server. Log in with your existing credentials.</p>
        <button className="primary" onClick={() => { window.location.href = "/login"; }}>
          Continue to login
        </button>
      </div>
    );
  }

  return (
    <div className="centered-card wide">
      <button className="link-button" onClick={onBack}>
        &larr; Back
      </button>
      <h1>Restore from a backup</h1>
      <p className="muted">
        Everything here happens in your browser. The seed and passphrase are never sent to the server.
      </p>
      <form onSubmit={submit}>
        <label>
          Backup file
          <input type="file" accept=".json" onChange={onFileChange} required />
          {fileName && <span className="muted">{fileName}</span>}
        </label>
        <fieldset>
          <legend>24-word recovery seed</legend>
          <div className="word-grid">
            {words.map((w, i) => (
              <input
                key={i}
                value={w}
                placeholder={`${i + 1}`}
                onChange={(e) => {
                  const next = [...words];
                  next[i] = e.target.value;
                  setWords(next);
                }}
              />
            ))}
          </div>
        </fieldset>
        <label>
          Passphrase
          <input type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} required />
        </label>
        {error && <p className="field-error">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Restoring..." : "Decrypt and restore"}
        </button>
      </form>
    </div>
  );
}

function MigrateLegacy({ onBack }: { onBack: () => void }) {
  const [oldDsn, setOldDsn] = useState("");
  const [oldEntropy, setOldEntropy] = useState("");
  const [secretsText, setSecretsText] = useState("");
  const [serversText, setServersText] = useState("");
  const [usersText, setUsersText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MigrateLegacyResponse | null>(null);

  function parseServers(): { system_id: string; ip_address: string }[] {
    return serversText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [system_id, ip_address] = line.split(",").map((s) => s.trim());
        return { system_id, ip_address };
      });
  }

  function parseUsers(): { email: string; password: string }[] {
    return usersText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [email, password] = line.split(",").map((s) => s.trim());
        return { email, password };
      });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<MigrateLegacyResponse>("/api/setup/migrate-legacy", {
        old_dsn: oldDsn,
        old_entropy: oldEntropy,
        secrets: secretsText.split("\n").map((s) => s.trim()).filter(Boolean),
        app_servers: parseServers(),
        users: parseUsers(),
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="centered-card wide">
        <h1>Migration complete</h1>
        <ul className="summary-list">
          <li>{result.secrets_migrated} secret(s) migrated</li>
          <li>{result.app_servers_migrated} server(s) migrated</li>
          <li>{result.users_migrated} user(s) migrated</li>
          <li>{result.skipped} skipped (already present)</li>
          <li>{result.failed} failed</li>
        </ul>
        {result.log.length > 0 && (
          <pre className="log-output">{result.log.join("\n")}</pre>
        )}
        <button className="primary" onClick={() => { window.location.href = "/login"; }}>
          Continue to login
        </button>
      </div>
    );
  }

  return (
    <div className="centered-card wide">
      <button className="link-button" onClick={onBack}>
        &larr; Back
      </button>
      <h1>Migrate from a legacy server</h1>
      <p className="muted">
        The old server's system was never able to recover secret names, server ids, or IP addresses from ciphertext
        alone -- list the ones you know below. Migrated users keep their existing password and authenticator codes.
      </p>
      <form onSubmit={submit}>
        <label>
          Old database connection string
          <input
            value={oldDsn}
            onChange={(e) => setOldDsn(e.target.value)}
            placeholder="postgresql://cryptmaster:oldpass@old-host:5432/cryptmaster_db"
            required
          />
        </label>
        <label>
          Old .entropy file contents
          <textarea value={oldEntropy} onChange={(e) => setOldEntropy(e.target.value)} rows={2} required />
        </label>
        <label>
          Secret names (one per line)
          <textarea value={secretsText} onChange={(e) => setSecretsText(e.target.value)} rows={3} />
        </label>
        <label>
          App servers -- one per line, as "system_id, ip_address"
          <textarea value={serversText} onChange={(e) => setServersText(e.target.value)} rows={3} />
        </label>
        <label>
          Users -- one per line, as "email, current password"
          <textarea value={usersText} onChange={(e) => setUsersText(e.target.value)} rows={3} />
        </label>
        {error && <p className="field-error">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Migrating..." : "Run migration"}
        </button>
      </form>
    </div>
  );
}
