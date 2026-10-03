import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Save, Search, CheckCircle2 } from "lucide-react";
import { api, errorText, human, clock } from "../api";
import {
  useData,
  PageHead,
  IncidentTable,
  Pager,
  ErrorBox,
  Loading,
  Badge,
  VideoPlayer,
} from "../components";

export function Incidents() {
  const [filters, setFilters] = useState({
      search: "",
      status: "",
      category: "",
      store_id: "",
      date: "",
      camera_id: "",
      reviewer_id: "",
    }),
    [page, setPage] = useState(1),
    [query, setQuery] = useState("");
  const items = useData(`/incidents?page=${page}&${query}`, 5000),
    stores = useData("/stores");
  function apply(e) {
    e.preventDefault();
    setPage(1);
    setQuery(new URLSearchParams(filters).toString());
  }
  const field = (key, value) => setFilters({ ...filters, [key]: value });
  return (
    <>
      <PageHead
        title="Incident queue"
        subtitle="Human-created cases. Evidence and context for every decision."
      >
        <a className="secondary" href="/api/reports/incidents.csv">
          <Download size={16} />
          Export all accessible
        </a>
      </PageHead>
      <form className="panel filters" onSubmit={apply}>
        <label className="search-field">
          Search
          <input
            value={filters.search}
            onChange={(e) => field("search", e.target.value)}
            placeholder="Incident ID or notes…"
          />
        </label>
        <label>
          Status
          <select
            aria-label="Status"
            value={filters.status}
            onChange={(e) => field("status", e.target.value)}
          >
            <option value="">All statuses</option>
            {[
              "NEEDS_REVIEW",
              "IN_REVIEW",
              "NOT_AN_INCIDENT",
              "ESCALATED",
              "CLOSED",
            ].map((v) => (
              <option key={v} value={v}>
                {human(v)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Store
          <select
            value={filters.store_id}
            onChange={(e) => field("store_id", e.target.value)}
          >
            <option value="">All stores</option>
            {stores.data?.map((s) => (
              <option value={s.id} key={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select
            value={filters.category}
            onChange={(e) => field("category", e.target.value)}
          >
            <option value="">All categories</option>
            {[
              "checkout_anomaly",
              "item_handling",
              "zone_transition",
              "possible_scan_mismatch",
              "other",
            ].map((v) => (
              <option key={v} value={v}>
                {human(v)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Created date (UTC)
          <input
            type="date"
            value={filters.date}
            onChange={(e) => field("date", e.target.value)}
          />
        </label>
        <label>
          Camera
          <input
            value={filters.camera_id}
            onChange={(e) => field("camera_id", e.target.value)}
            placeholder="Exact camera name"
          />
        </label>
        <label>
          Assignee ID
          <input
            value={filters.reviewer_id}
            onChange={(e) => field("reviewer_id", e.target.value)}
            placeholder="USR-…"
          />
        </label>
        <button className="primary">
          <Search size={16} />
          Apply filters
        </button>
      </form>
      <ErrorBox>{items.error || stores.error}</ErrorBox>
      <section className="panel">
        <div className="panel-head">
          <h2>
            Cases <span className="count">{items.data?.total || 0}</span>
          </h2>
          <span className="subtle">Newest first</span>
        </div>
        {items.data ? (
          <>
            <IncidentTable items={items.data.items} />
            <Pager
              page={page}
              total={items.data.total}
              size={25}
              onChange={setPage}
            />
          </>
        ) : (
          <Loading />
        )}
      </section>
    </>
  );
}

export function Investigation({ user }) {
  const { id } = useParams(),
    record = useData(`/incidents/${id}`, 4000),
    audit = useData(`/incidents/${id}/audit`, 5000),
    users = useData(user.role === "admin" ? "/users" : "/auth/me");
  const [status, setStatus] = useState("IN_REVIEW"),
    [notes, setNotes] = useState(""),
    [version, setVersion] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [success, setSuccess] = useState(""),
    [mode, setMode] = useState("original");
  const loaded = useRef(false);
  const i = record.data;
  useEffect(() => {
    loaded.current = false;
    setVersion(null);
    api.post(`/incidents/${id}/opened`).catch(() => {});
  }, [id]);
  useEffect(() => {
    if (i && !loaded.current) {
      setNotes(i.notes);
      setStatus(i.status === "NEEDS_REVIEW" ? "IN_REVIEW" : i.status);
      setVersion(i.version);
      loaded.current = true;
    }
  }, [i]);
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const r = await api.post(`/incidents/${id}/review`, {
        status,
        notes,
        version,
      });
      setVersion(r.data.version);
      await record.reload();
      await audit.reload();
      setSuccess("Review saved. Decision added to the audit history.");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function reloadReview() {
    const doc = await record.reload();
    if (doc) {
      setNotes(doc.notes);
      setStatus(doc.status);
      setVersion(doc.version);
      setError("");
    }
  }
  async function assign(e) {
    setBusy(true);
    setError("");
    try {
      const r = await api.patch(`/incidents/${id}/assignment`, {
        reviewer_id: e.target.value || null,
        version: i.version,
      });
      setVersion(r.data.version);
      await record.reload();
      await audit.reload();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function retry() {
    try {
      await api.post(`/incidents/${id}/evidence/retry`);
      await record.reload();
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <>
      <Link className="back" to="/incidents">
        <ArrowLeft size={16} />
        Incident queue
      </Link>
      <ErrorBox>{record.error}</ErrorBox>
      {!i ? (
        <Loading />
      ) : (
        <>
          <PageHead
            eyebrow="INVESTIGATION"
            title={i.id}
            subtitle={`${i.camera_id} · ${human(i.category)} · ${clock(i.timestamp)}`}
          >
            <Badge value={i.status} />
          </PageHead>
          <div className="detail-grid">
            <div>
              <section className="panel">
                <div className="panel-head">
                  <h2>Evidence viewer</h2>
                  <div className="tabs">
                    <button
                      className={mode === "original" ? "selected" : ""}
                      onClick={() => setMode("original")}
                    >
                      Full video
                    </button>
                    <button
                      disabled={i.evidence_status !== "ready"}
                      className={mode === "clip" ? "selected" : ""}
                      onClick={() => setMode("clip")}
                    >
                      Evidence clip
                    </button>
                  </div>
                </div>
                <VideoPlayer
                  src={
                    mode === "clip"
                      ? `/api/incidents/${id}/evidence/clip`
                      : `/api/videos/${i.video_id}/media`
                  }
                  eventTime={
                    mode === "clip"
                      ? i.timestamp - (i.clip_start || 0)
                      : i.timestamp
                  }
                />
                <div className="padded compact">
                  <span className="subtle">
                    Evidence: {human(i.evidence_status)}
                  </span>
                  {i.evidence_status === "failed" && (
                    <>
                      <ErrorBox>{i.evidence_error}</ErrorBox>
                      <button onClick={retry}>Retry clip generation</button>
                    </>
                  )}
                  <div className="export-links">
                    <a href={`/api/incidents/${id}/report?format=pdf`}>
                      <Download size={14} />
                      PDF report
                    </a>
                    <a href={`/api/incidents/${id}/report?format=json`}>JSON</a>
                    {i.evidence_status === "ready" && (
                      <a
                        href={`/api/incidents/${id}/evidence/clip`}
                        download={`${id}.mp4`}
                      >
                        Download clip
                      </a>
                    )}
                  </div>
                </div>
              </section>
              <section className="panel padded">
                <h2>Case context</h2>
                <dl className="facts">
                  <div>
                    <dt>Store</dt>
                    <dd>{i.store_id}</dd>
                  </div>
                  <div>
                    <dt>Camera</dt>
                    <dd>{i.camera_id}</dd>
                  </div>
                  <div>
                    <dt>Review priority</dt>
                    <dd>
                      <Badge value={i.priority} />
                    </dd>
                  </div>
                  <div>
                    <dt>Created</dt>
                    <dd>{new Date(i.created_at).toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt>Source</dt>
                    <dd>Human-created incident</dd>
                  </div>
                  <div>
                    <dt>Video</dt>
                    <dd>
                      <Link className="text-link" to={`/videos/${i.video_id}`}>
                        Open observations →
                      </Link>
                    </dd>
                  </div>
                </dl>
                {user.role === "admin" && (
                  <label>
                    Assigned reviewer
                    <select
                      value={i.reviewer_id || ""}
                      disabled={busy}
                      onChange={assign}
                    >
                      <option value="">Unassigned</option>
                      {users.data
                        ?.filter?.((u) => !u.disabled)
                        .map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.name} · {u.role}
                          </option>
                        ))}
                    </select>
                  </label>
                )}
              </section>
              <section className="panel padded">
                <h2>Audit history</h2>
                <ErrorBox>{audit.error}</ErrorBox>
                <div className="audit">
                  {audit.data?.history
                    .slice()
                    .reverse()
                    .map((a, n) => (
                      <article key={n}>
                        <i />
                        <div>
                          <strong>
                            {human(a.action)}{" "}
                            {a.status && `· ${human(a.status)}`}
                          </strong>
                          <small>
                            {new Date(a.at).toLocaleString()} · {a.actor}
                          </small>
                          <p>{a.notes}</p>
                        </div>
                      </article>
                    ))}
                </div>
                <details>
                  <summary>Access log</summary>
                  {audit.data?.access_log.map((a) => (
                    <p className="muted" key={a.id}>
                      {new Date(a.at).toLocaleString()} · {human(a.action)} ·{" "}
                      {a.actor}
                    </p>
                  ))}
                </details>
              </section>
            </div>
            <aside>
              <section className="panel padded sticky">
                <span className="eyebrow">INVESTIGATOR DECISION</span>
                <h2>Record your review</h2>
                <p>
                  Review the surrounding footage before selecting an outcome.
                </p>
                <form onSubmit={save} className="stack">
                  <label>
                    Outcome
                    <select
                      aria-label="Outcome"
                      value={status}
                      onChange={(e) => setStatus(e.target.value)}
                    >
                      {[
                        ["IN_REVIEW", "Needs more review"],
                        ["NOT_AN_INCIDENT", "Not an incident"],
                        ["ESCALATED", "Escalate for investigation"],
                        ["CLOSED", "Close case"],
                        ["NEEDS_REVIEW", "Return to review queue"],
                      ].map(([value, label]) => (
                        <option value={value} key={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Investigator notes
                    <textarea
                      rows="8"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      maxLength="5000"
                      required
                    />
                  </label>
                  <ErrorBox>{error}</ErrorBox>
                  {version !== null && i.version !== version && (
                    <div className="notice">
                      This case changed while you were editing.{" "}
                      <button type="button" onClick={reloadReview}>
                        Load latest review
                      </button>
                    </div>
                  )}
                  {success && (
                    <div className="success">
                      <CheckCircle2 size={16} />
                      {success}
                    </div>
                  )}
                  <button
                    className="primary"
                    disabled={busy || version === null}
                  >
                    <Save size={16} />
                    {busy ? "Saving…" : "Save review"}
                  </button>
                  <small>
                    Each submitted decision and note remains in the case
                    history.
                  </small>
                </form>
              </section>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
