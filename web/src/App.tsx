import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { SetupPage } from "./pages/SetupPage";
import { LoginPage } from "./pages/LoginPage";
import { FirstLoginPage } from "./pages/FirstLoginPage";
import { DashboardLayout } from "./pages/DashboardLayout";
import { ServersPage } from "./pages/ServersPage";
import { SecretsPage } from "./pages/SecretsPage";
import { UsersPage } from "./pages/UsersPage";
import { LogsPage } from "./pages/LogsPage";
import { BackupPage } from "./pages/BackupPage";
import { AccountPage } from "./pages/AccountPage";

function useSetupStatus() {
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(true);

  useEffect(() => {
    api
      .get<{ initialized: boolean }>("/api/setup/status")
      .then((res) => setInitialized(res.initialized))
      .finally(() => setLoading(false));
  }, []);

  return { loading, initialized };
}

function Gate() {
  const setup = useSetupStatus();
  const { loading: authLoading, session } = useAuth();

  if (setup.loading || authLoading) {
    return <div className="full-page-loading">Loading...</div>;
  }

  if (!setup.initialized) {
    return (
      <Routes>
        <Route path="*" element={<SetupPage />} />
      </Routes>
    );
  }

  if (!session) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  if (session.must_change_password) {
    return (
      <Routes>
        <Route path="/first-login" element={<FirstLoginPage />} />
        <Route path="*" element={<Navigate to="/first-login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<ServersPage />} />
        <Route path="/secrets" element={<SecretsPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/logs" element={<LogsPage />} />
        {session.role === "admin" && <Route path="/backup" element={<BackupPage />} />}
        <Route path="/account" element={<AccountPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </BrowserRouter>
  );
}
