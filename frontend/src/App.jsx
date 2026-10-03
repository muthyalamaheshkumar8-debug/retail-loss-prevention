import React, { useEffect, useState } from "react";
import { NavLink, Routes, Route, Navigate, Link } from "react-router-dom";
import {
  ShieldCheck,
  LayoutDashboard,
  Film,
  ListChecks,
  ChartNoAxesCombined,
  Store,
  FileText,
  Settings,
  LogOut,
  History,
  ArrowUpRight,
  Menu,
} from "lucide-react";
import { api, errorText } from "./api";
import { ErrorBox, Loading } from "./components";
import {
  Dashboard,
  Analytics,
  Reports,
  Investigations,
} from "./pages/Overview";
import { Videos, VideoDetail } from "./pages/Videos";
import { Incidents, Investigation } from "./pages/Incidents";
import { Stores, SettingsPage } from "./pages/Admin";

function Login({ onLogin }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const values = Object.fromEntries(new FormData(e.currentTarget));
      const r = await api.post("/auth/login", values);
      onLogin(r.data);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login">
      <section className="login-story">
        <div className="brand">
          <ShieldCheck />
          <span>
            retail<span className="brand-light">review</span>
          </span>
        </div>
        <div>
          <span className="eyebrow">VIDEO INVESTIGATION WORKSPACE</span>
          <h1>
            Clarity in every frame.
            <br />
            <em>Judgment stays human.</em>
          </h1>
          <p>
            Bring footage, observations, and evidence together in one focused
            review workspace.
          </p>
        </div>
        <small>Observe · Review · Document</small>
      </section>
      <section className="login-form">
        <form onSubmit={submit}>
          <span className="eyebrow">WELCOME BACK</span>
          <h2>Open your workspace</h2>
          <p>Sign in with your investigator account.</p>
          <label>
            Email address
            <input
              name="email"
              type="email"
              required
              autoComplete="username"
              placeholder="you@yourstore.com"
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              required
              autoComplete="current-password"
            />
          </label>
          <ErrorBox>{error}</ErrorBox>
          <button className="primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
            <ArrowUpRight size={18} />
          </button>
          <small>
            Your administrator manages access. For a new installation, use the
            credentials in your local .env file.
          </small>
        </form>
      </section>
    </div>
  );
}
export default function App() {
  const [user, setUser] = useState(undefined),
    [menu, setMenu] = useState(false),
    [authError, setAuthError] = useState("");
  useEffect(() => {
    api
      .get("/auth/me")
      .then((r) => setUser(r.data))
      .catch((e) => {
        if (e.response?.status === 401) setUser(null);
        else setAuthError(errorText(e));
      });
    const id = api.interceptors.response.use(
      (r) => r,
      (e) => {
        if (e.response?.status === 401 && !e.config.url.includes("/auth/"))
          setUser(null);
        return Promise.reject(e);
      },
    );
    return () => api.interceptors.response.eject(id);
  }, []);
  if (authError)
    return (
      <div className="login-form">
        <div>
          <ErrorBox>{authError}</ErrorBox>
          <button onClick={() => location.reload()}>Retry connection</button>
        </div>
      </div>
    );
  if (user === undefined) return <Loading />;
  if (!user) return <Login onLogin={setUser} />;
  const nav = [
    ["/", "Overview", LayoutDashboard],
    ["/videos", "Video library", Film],
    ["/incidents", "Incident queue", ListChecks],
    ["/investigations", "Review history", History],
    ["/analytics", "Analytics", ChartNoAxesCombined],
    ["/stores", "Stores & cameras", Store],
    ["/reports", "Reports", FileText],
    ["/settings", "Settings", Settings],
  ];
  async function logout() {
    await api.post("/auth/logout");
    setUser(null);
  }
  return (
    <div className="shell">
      <aside className={menu ? "sidebar open" : "sidebar"}>
        <Link to="/" className="brand">
          <ShieldCheck size={29} />
          <span>
            retail<span className="brand-light">review</span>
          </span>
        </Link>
        <div className="workspace-tag">
          <span className="dot" />
          Investigation workspace
        </div>
        <div className="nav-label">OPERATIONS</div>
        <nav>
          {nav.map(([path, label, Icon]) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/"}
              onClick={() => setMenu(false)}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="human-note">
            <ShieldCheck size={18} />
            <span>
              AI observes.
              <br />
              People decide.
            </span>
          </div>
          <div className="profile">
            <div className="avatar">{user.name.slice(0, 1)}</div>
            <div>
              <strong>{user.name}</strong>
              <small>{user.role}</small>
            </div>
            <button aria-label="Sign out" onClick={logout}>
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main">
        <div className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMenu(!menu)}
            aria-label="Open navigation"
          >
            <Menu />
          </button>
          <span>
            OPERATIONS / <b>RETAIL REVIEW</b>
          </span>
          <span className="top-date">
            {new Date().toLocaleDateString(undefined, {
              weekday: "short",
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </span>
        </div>
        <main>
          {import.meta.env.VITE_FREE_HOSTING_MODE === "true" && (
            <p className="hosting-notice" role="note">
              Free demo: person tracking is disabled. Uploaded videos and
              evidence are temporary and can disappear when the server sleeps or
              restarts. Download evidence you want to keep.
            </p>
          )}
          <Routes>
            <Route path="/" element={<Dashboard user={user} />} />
            <Route path="/videos" element={<Videos />} />
            <Route path="/videos/:id" element={<VideoDetail />} />
            <Route path="/incidents" element={<Incidents />} />
            <Route
              path="/incidents/:id"
              element={<Investigation user={user} />}
            />
            <Route path="/investigations" element={<Investigations />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/stores" element={<Stores user={user} />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<SettingsPage user={user} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer>
          Retail Review <span>Evidence-led. Human-reviewed.</span>
        </footer>
      </div>
    </div>
  );
}
