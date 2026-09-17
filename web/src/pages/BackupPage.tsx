import { useState } from "react";
import { api, ApiError, type BackupExportResponse } from "../api/client";
import { generateMnemonic } from "../crypto/bip39";
import { encryptBackup } from "../crypto/backupFile";

type Step = "start" | "auth" | "seed-display" | "seed-confirm" | "passphrase" | "done";

export function BackupPage() {
  const [step, setStep] = useState<Step>("start");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [exportedData, setExportedData] = useState<Record<string, unknown> | null>(null);
  const [mnemonic, setMnemonic] = useState<string[]>([]);
  const [confirmWords, setConfirmWords] = useState<string[]>(Array(24).fill(""));
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [passphrase, setPassphrase] = useState("");
  const [passphraseConfirm, setPassphraseConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitAuth(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<BackupExportResponse>("/api/backup/export", { password, otp });
      const words = await generateMnemonic();
      setExportedData(res.data);
      setMnemonic(words);
      setStep("seed-display");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  function submitConfirmWords(e: React.FormEvent) {
    e.preventDefault();
    const typed = confirmWords.map((w) => w.trim().toLowerCase());
    const expected = mnemonic.map((w) => w.toLowerCase());
    if (JSON.stringify(typed) !== JSON.stringify(expected)) {
      setConfirmError("That doesn't match what was shown. Go back and re-check what you wrote down.");
      return;
    }
    setConfirmError(null);
    setStep("passphrase");
  }

  async function submitPassphrase(e: React.FormEvent) {
    e.preventDefault();
    if (passphrase !== passphraseConfirm) {
      setError("Passphrases do not match.");
      return;
    }
    if (passphrase.length < 8) {
      setError("Passphrase must be at least 8 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const blob = await encryptBackup(exportedData, mnemonic, passphrase);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cryptmaster-backup-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStep("done");
    } catch {
      setError("Failed to encrypt the backup.");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setStep("start");
    setPassword("");
    setOtp("");
    setExportedData(null);
    setMnemonic([]);
    setConfirmWords(Array(24).fill(""));
    setPassphrase("");
    setPassphraseConfirm("");
    setError(null);
    setConfirmError(null);
  }

  if (step === "start") {
    return (
      <div>
        <h1>Backup</h1>
        <p className="muted">
          Exports everything in the vault, encrypted in your browser with a fresh 24-word seed and a passphrase you
          choose. Neither ever reaches the server, and neither is stored anywhere -- if you lose them, the backup is
          unrecoverable.
        </p>
        <button className="primary" onClick={() => setStep("auth")}>
          Start a backup
        </button>
      </div>
    );
  }

  if (step === "auth") {
    return (
      <div className="card-form">
        <h1>Confirm it's you</h1>
        <p className="muted">Re-enter your password and a fresh one-time code before exporting the whole vault.</p>
        <form onSubmit={submitAuth}>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <label>
            One-time code
            <input value={otp} onChange={(e) => setOtp(e.target.value)} required />
          </label>
          {error && <p className="field-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" onClick={reset}>
              Cancel
            </button>
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Verifying..." : "Continue"}
            </button>
          </div>
        </form>
      </div>
    );
  }

  if (step === "seed-display") {
    return (
      <div className="card-form">
        <h1>Write down these 24 words</h1>
        <p className="muted">
          This is the only time this seed will ever be shown. Write it down by hand, in order, and keep it somewhere
          safe and offline. On the next screen it will be hidden and you'll be asked to type it back in.
        </p>
        <div className="word-grid word-grid-display">
          {mnemonic.map((w, i) => (
            <div key={i} className="word-chip">
              <span className="word-index">{i + 1}</span>
              {w}
            </div>
          ))}
        </div>
        <button className="primary" onClick={() => setStep("seed-confirm")}>
          I've written it down
        </button>
      </div>
    );
  }

  if (step === "seed-confirm") {
    return (
      <div className="card-form">
        <h1>Confirm your seed</h1>
        <p className="muted">Type the 24 words back in, in order, to prove you wrote them down correctly.</p>
        <form onSubmit={submitConfirmWords}>
          <div className="word-grid">
            {confirmWords.map((w, i) => (
              <input
                key={i}
                value={w}
                placeholder={`${i + 1}`}
                onChange={(e) => {
                  const next = [...confirmWords];
                  next[i] = e.target.value;
                  setConfirmWords(next);
                }}
                autoComplete="off"
                autoCapitalize="off"
                spellCheck={false}
              />
            ))}
          </div>
          {confirmError && <p className="field-error">{confirmError}</p>}
          <button className="primary" type="submit">
            Confirm
          </button>
        </form>
      </div>
    );
  }

  if (step === "passphrase") {
    return (
      <div className="card-form">
        <h1>Choose a passphrase</h1>
        <p className="muted">
          This acts like a 25th word: both the seed and this passphrase are required to decrypt the backup.
        </p>
        <form onSubmit={submitPassphrase}>
          <label>
            Passphrase
            <input type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} required />
          </label>
          <label>
            Confirm passphrase
            <input
              type="password"
              value={passphraseConfirm}
              onChange={(e) => setPassphraseConfirm(e.target.value)}
              required
            />
          </label>
          {error && <p className="field-error">{error}</p>}
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Encrypting..." : "Encrypt and download"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div>
      <h1>Backup downloaded</h1>
      <p>Store the file, the 24 words, and the passphrase in separate, safe places.</p>
      <button className="primary" onClick={reset}>
        Done
      </button>
    </div>
  );
}
