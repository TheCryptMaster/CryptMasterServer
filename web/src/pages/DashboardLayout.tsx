import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function DashboardLayout() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="brand">Crypt Master</div>
        <NavLink to="/" end>
          Servers
        </NavLink>
        <NavLink to="/secrets">Secrets</NavLink>
        <NavLink to="/users">Users</NavLink>
        <NavLink to="/logs">Logs</NavLink>
        {session?.role === "admin" && <NavLink to="/backup">Backup</NavLink>}
        <NavLink to="/account">My account</NavLink>
        <div className="spacer" />
        <div className="role-badge">{session?.role}</div>
        <button className="link-button" onClick={handleLogout}>
          Sign out
        </button>
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
