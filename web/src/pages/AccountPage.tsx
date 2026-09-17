import { useState } from "react";
import { api, ApiError, type ChangePasswordResponse } from "../api/client";
import { QrCode } from "../components/QrCode";
import { useAuth } from "../auth/AuthContext";

type Step = "idle" | "password" | "enroll" | "confirm" | "done";

export function AccountPage() {
  const [step, setStep] = useState<Step>("idle");
  const [currentPassword, setCurrentPassword] = useState("");
  const [currentOtp, setCurrentOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [provisioningUri, setProvisioningUri] = useState("");
  const [confirmOtp, setConfirmOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { session } = useAuth();

  function reset() {
    setStep("idle");
    setCurrentPassword("");
    setCurrentOtp("");
    setNewPassword("");
    setConfirmPassword("");
    setConfirmOtp("");
    setError(null);
  }

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
        current_otp: currentOtp,
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
      setStep("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>My account</h1>
      <p className="muted">Role: {session?.role}</p>

      {step === "idle" && (
        <button className="primary" onClick={() => setStep("password")}>
          Change password / re-enroll authenticator
        </button>
      )}

      {step === "password" && (
        <form onSubmit={submitPasswordChange} className="card-form">
          <p className="muted">Changing your password rotates your authenticator seed -- you'll re-enroll it next.</p>
          <label>
            Current password
            <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
          </label>
          <label>
            Current one-time code
            <input value={currentOtp} onChange={(e) => setCurrentOtp(e.target.value)} required />
          </label>
          <label>
            New password
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
          </label>
          <label>
            Confirm new password
            <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
          </label>
          {error && <p className="field-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" onClick={reset}>
              Cancel
            </button>
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Saving..." : "Continue"}
            </button>
          </div>
        </form>
      )}

      {step === "enroll" && (
        <div className="card-form">
          <p className="muted">Scan this with your authenticator app, then continue.</p>
          <QrCode data={provisioningUri} />
          <button className="primary" onClick={() => setStep("confirm")}>
            I've added it
          </button>
        </div>
      )}

      {step === "confirm" && (
        <form onSubmit={submitConfirm} className="card-form">
          <label>
            New one-time code
            <input value={confirmOtp} onChange={(e) => setConfirmOtp(e.target.value)} required />
          </label>
          {error && <p className="field-error">{error}</p>}
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Confirming..." : "Confirm"}
          </button>
        </form>
      )}

      {step === "done" && (
        <div className="card-form">
          <p>Password and authenticator updated.</p>
          <button className="primary" onClick={reset}>
            Done
          </button>
        </div>
      )}
    </div>
  );
}
