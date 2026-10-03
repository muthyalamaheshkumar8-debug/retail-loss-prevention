import React, { useState } from "react";
import { Plus, Store as StoreIcon, Camera, UserPlus, Save } from "lucide-react";
import { api, errorText } from "../api";
import {
  useData,
  PageHead,
  ErrorBox,
  Loading,
  Empty,
  Badge,
} from "../components";

export function Stores({ user }) {
  const stores = useData("/stores"),
    [edit, setEdit] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const form = e.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    values.cameras = values.cameras
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    try {
      if (edit?.id) await api.put(`/stores/${edit.id}`, values);
      else await api.post("/stores", values);
      form.reset();
      setEdit(null);
      await stores.reload();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHead
        title="Stores & cameras"
        subtitle="Organize your video sources by location and camera."
      />
      <ErrorBox>{error || stores.error}</ErrorBox>
      {user.role === "admin" && (
        <section className="panel padded">
          <h2>{edit ? "Edit store" : "Add a store"}</h2>
          <form key={edit?.id || "new"} className="inline-form" onSubmit={save}>
            <label>
              Store name
              <input
                name="name"
                required
                maxLength="100"
                defaultValue={edit?.name}
              />
            </label>
            <label>
              Location
              <input
                name="location"
                maxLength="200"
                defaultValue={edit?.location}
              />
            </label>
            <label>
              Camera names, comma separated
              <input
                name="cameras"
                required
                defaultValue={edit?.cameras.join(", ")}
                placeholder="Checkout 01, Entrance"
              />
            </label>
            <button className="primary" disabled={busy}>
              <Save size={16} />
              {edit ? "Save changes" : "Create store"}
            </button>
            {edit && (
              <button type="button" onClick={() => setEdit(null)}>
                Cancel
              </button>
            )}
          </form>
        </section>
      )}
      {!stores.data ? (
        <Loading />
      ) : stores.data.length ? (
        <div className="store-grid">
          {stores.data.map((s) => (
            <section className="panel padded" key={s.id}>
              <div className="store-title">
                <StoreIcon size={25} />
                <Badge value="active" />
              </div>
              <h2>{s.name}</h2>
              <p>{s.location || "Location not specified"}</p>
              <small>{s.id}</small>
              <div className="camera-list">
                {s.cameras.map((c) => (
                  <span key={c}>
                    <Camera size={14} />
                    {c}
                  </span>
                ))}
              </div>
              {user.role === "admin" && (
                <button className="secondary" onClick={() => setEdit(s)}>
                  Edit store
                </button>
              )}
            </section>
          ))}
        </div>
      ) : (
        <section className="panel">
          <Empty title="Add your first location">
            An administrator can add stores and name their cameras above.
          </Empty>
        </section>
      )}
    </>
  );
}
export function SettingsPage({ user }) {
  const settings = useData("/settings"),
    users = useData(user.role === "admin" ? "/users" : "/auth/me"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function create(e) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    setError("");
    try {
      await api.post("/users", Object.fromEntries(new FormData(form)));
      form.reset();
      await users.reload();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function toggle(u) {
    setError("");
    try {
      await api.patch(`/users/${u.id}/disabled?disabled=${!u.disabled}`);
      await users.reload();
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <>
      <PageHead
        title="Workspace settings"
        subtitle="Processing configuration and access management."
      />
      <ErrorBox>{error || settings.error || users.error}</ErrorBox>
      <section className="panel padded">
        <h2>Processing engine</h2>
        {settings.data && (
          <dl className="facts">
            <div>
              <dt>Computer vision</dt>
              <dd>{settings.data.cv_enabled ? "Enabled" : "Disabled"}</dd>
            </div>
            <div>
              <dt>Detector</dt>
              <dd>{settings.data.model}</dd>
            </div>
            <div>
              <dt>Tracking</dt>
              <dd>{settings.data.tracking}</dd>
            </div>
            <div>
              <dt>Upload limit</dt>
              <dd>
                {settings.data.max_upload_mb} MB /{" "}
                {settings.data.max_duration_minutes} minutes
              </dd>
            </div>
          </dl>
        )}
        <p className="muted">
          Server settings are configured in .env. Restart the services after
          changing them.
        </p>
      </section>
      {user.role === "admin" && (
        <>
          <section className="panel padded">
            <h2>Add a team member</h2>
            <form className="inline-form" onSubmit={create}>
              <label>
                Full name
                <input name="name" required maxLength="100" />
              </label>
              <label>
                Email
                <input name="email" type="email" required />
              </label>
              <label>
                Initial password
                <input
                  name="password"
                  type="password"
                  minLength="12"
                  maxLength="256"
                  required
                  autoComplete="new-password"
                />
              </label>
              <label>
                Role
                <select name="role">
                  <option value="investigator">Investigator</option>
                  <option value="reviewer">Reviewer</option>
                  <option value="admin">Administrator</option>
                </select>
              </label>
              <button className="primary" disabled={busy}>
                <UserPlus size={16} />
                Add user
              </button>
            </form>
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Team access</h2>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email / user ID</th>
                    <th>Role</th>
                    <th>Access</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {users.data?.map?.((u) => (
                    <tr key={u.id}>
                      <td>{u.name}</td>
                      <td>
                        {u.email}
                        <small>{u.id}</small>
                      </td>
                      <td>
                        <Badge value={u.role} />
                      </td>
                      <td>{u.disabled ? "Disabled" : "Active"}</td>
                      <td>
                        {u.id !== user.id && (
                          <button onClick={() => toggle(u)}>
                            {u.disabled ? "Enable" : "Disable"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
