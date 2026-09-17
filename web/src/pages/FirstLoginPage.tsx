import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, type ChangePasswordResponse } from "../api/client";
import { QrCode } from "../components/QrCode";
import { useAuth } from "../auth/AuthContext";

type Step = "password" | "enroll" | "confirm";

export function FirstLoginPage() {
  const [step, setStep] = useState<Step>("password");
  const [currentPassword, setCurrentPassword] = useState("");
  const [currentOtp, setCurrentOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [provisioningUri, setProvisioningUri] = useState("");
  const [confirmOtp, setConfirmOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { session, refresh } = useAuth();
  const navigate = useNavigate();

  async function submitPasswordChange(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (newPassword.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<ChangePasswordResponse>("/api/auth/change-password", {
        current_password: currentPassword,
        current_otp: session?.must_change_password ? undefined : currentOtp,
        new_password: newPassword,
      });
      setProvisioningUri(res.provisioning_uri);
      setStep("enroll");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function submitConfirm(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/auth/confirm-otp", { otp: confirmOtp });
      await refresh();
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  if (step === "password") {
    return (
      <div className="centered-card">
        <h1>Set a new password</h1>
        <p className="muted">
          {session?.must_change_password
            ? "You're using default credentials. Choose a new password before continuing."
            : "Changing your password rotates your authenticator seed too -- you'll re-enroll it next."}
        </p>
        <form onSubmit={submitPasswordChange}>
          <label>
            Current password
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {!session?.must_change_password && (
            <label>
              Current one-time code
              <input value={currentOtp} onChange={(e) => setCurrentOtp(e.target.value)} required />
            </label>
          )}
          <label>
            New password (at least 12 characters)
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
          <label>
            Confirm new password
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
          {error && <p className="field-error">{error}</p>}
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Saving..." : "Continue"}
          </button>
        </form>
      </div>
    );
  }

  if (step === "enroll") {
    return (
      <div className="centered-card">
        <h1>Scan this code</h1>
        <p className="muted">Add it to your authenticator app now, then continue.</p>
        <QrCode data={provisioningUri} />
        <details>
          <summary>Can't scan it?</summary>
          <code className="wrap">{provisioningUri}</code>
        </details>
        <button className="primary" onClick={() => setStep("confirm")}>
          I've added it
        </button>
      </div>
    );
  }

  return (
    <div className="centered-card">
      <h1>Confirm your code</h1>
      <p className="muted">Enter the current 6-digit code from your authenticator app to finish setup.</p>
      <form onSubmit={submitConfirm}>
        <label>
          One-time code
          <input value={confirmOtp} onChange={(e) => setConfirmOtp(e.target.value)} inputMode="numeric" required />
        </label>
        {error && <p className="field-error">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Confirming..." : "Confirm"}
        </button>
      </form>
    </div>
  );
}
