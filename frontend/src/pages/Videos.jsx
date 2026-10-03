import React, { useState, useRef } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import {
  Upload,
  Film,
  ArrowLeft,
  Plus,
  Trash2,
  Play,
  ScanLine,
} from "lucide-react";
import { api, errorText, human, clock } from "../api";
import {
  useData,
  PageHead,
  Badge,
  ErrorBox,
  Loading,
  Empty,
  Pager,
  VideoPlayer,
} from "../components";

export function Videos() {
  const [page, setPage] = useState(1),
    videos = useData(`/videos?page=${page}`, 4000),
    stores = useData("/stores"),
    limits = useData("/settings");
  const [store, setStore] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [progress, setProgress] = useState(0);
  const navigate = useNavigate();
  async function upload(e) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    setError("");
    setProgress(0);
    try {
      const file = form.elements.file.files[0];
      if (!limits.data)
        throw Error("Wait for the server's upload limits to load");
      if (file.size > limits.data.max_upload_mb * 1024 * 1024)
        throw Error(`Maximum video size is ${limits.data.max_upload_mb} MB`);
      const r = await api.post("/videos/upload", new FormData(form), {
        onUploadProgress: (e) =>
          setProgress(Math.round((e.loaded / (e.total || 1)) * 100)),
      });
      navigate(`/videos/${r.data.id}`);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHead
        title="Video library"
        subtitle="Upload footage, define your zones, and create a reviewable record."
      />
      <section className="panel upload-panel">
        <div>
          <div className="upload-icon">
            <Upload />
          </div>
          <h2>Add store footage</h2>
          <p>
            MP4, MOV, AVI, MKV ·{" "}
            {limits.data
              ? `Up to ${limits.data.max_upload_mb} MB · Up to ${limits.data.max_duration_minutes} minutes`
              : "Loading upload limits…"}
          </p>
        </div>
        <form onSubmit={upload} className="upload-form">
          <label>
            Store
            <select
              aria-label="Store"
              name="store_id"
              value={store}
              required
              onChange={(e) => setStore(e.target.value)}
            >
              <option value="">Select store</option>
              {stores.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Camera
            <select aria-label="Camera" name="camera_id" key={store} required>
              <option value="">Select camera</option>
              {stores.data
                ?.find((s) => s.id === store)
                ?.cameras.map((c) => (
                  <option key={c}>{c}</option>
                ))}
            </select>
          </label>
          <label className="file-field">
            Video file
            <input
              name="file"
              type="file"
              accept=".mp4,.mov,.avi,.mkv"
              required
            />
          </label>
          <button
            className="primary"
            disabled={busy || !stores.data?.length || !limits.data}
          >
            <Upload size={16} />
            {busy ? `Uploading ${progress}%` : "Upload video"}
          </button>
        </form>
        <ErrorBox>{error || stores.error || limits.error}</ErrorBox>
        {stores.data?.length === 0 && (
          <p>
            <Link className="text-link" to="/stores">
              Add a store and camera first →
            </Link>
          </p>
        )}
      </section>
      <div className="section-title">
        <h2>
          All footage <span className="count">{videos.data?.total || 0}</span>
        </h2>
        <span className="subtle">Status refreshes automatically</span>
      </div>
      <ErrorBox>{videos.error}</ErrorBox>
      {!videos.data ? (
        <Loading />
      ) : videos.data.items.length ? (
        <>
          <div className="video-grid">
            {videos.data.items.map((v) => (
              <Link to={`/videos/${v.id}`} className="video-card" key={v.id}>
                <div className="video-cover">
                  <Film size={35} />
                  <span>{clock(v.duration)}</span>
                  <div className="cover-label">{v.camera_id}</div>
                </div>
                <div className="video-card-content">
                  <h3>{v.filename}</h3>
                  <p>{new Date(v.uploaded_at).toLocaleString()}</p>
                  <div>
                    <Badge value={v.status} />
                    <span className="subtle">
                      {Math.round(v.size / 1024 / 1024)} MB
                    </span>
                  </div>
                  {["QUEUED", "PROCESSING", "ANALYZING"].includes(v.status) && (
                    <progress max="100" value={v.progress} />
                  )}
                </div>
              </Link>
            ))}
          </div>
          <Pager
            page={page}
            total={videos.data.total}
            size={24}
            onChange={setPage}
          />
        </>
      ) : (
        <section className="panel">
          <Empty title="Start with your first video">
            Upload footage from an authorized source to begin.
          </Empty>
        </section>
      )}
    </>
  );
}

export function VideoDetail() {
  const { id } = useParams(),
    video = useData(`/videos/${id}`, 3000);
  const [eventPage, setEventPage] = useState(1),
    events = useData(`/videos/${id}/events?page=${eventPage}`, 5000),
    config = useData("/settings");
  const [zones, setZones] = useState([]),
    [detect, setDetect] = useState(true),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [overlay, setOverlay] = useState(true),
    [time, setTime] = useState(0),
    [selectedEvent, setSelectedEvent] = useState(null);
  const ref = useRef(),
    navigate = useNavigate();
  const v = video.data;
  function zoneChange(index, key, value) {
    setZones((z) =>
      z.map((item, i) =>
        i === index
          ? { ...item, [key]: key === "name" ? value : Number(value) }
          : item,
      ),
    );
  }
  async function process() {
    setBusy(true);
    setError("");
    try {
      await api.post(`/videos/${id}/process`, {
        detect: detect && config.data?.cv_enabled,
        zones,
      });
      await video.reload();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function create(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const values = Object.fromEntries(new FormData(e.currentTarget));
      const r = await api.post("/incidents", {
        ...values,
        video_id: id,
        timestamp: Number(values.timestamp),
        event_id: selectedEvent,
      });
      navigate(`/incidents/${r.data.id}`);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const seek = (event) => {
    setTime(event.timestamp);
    setSelectedEvent(event.id);
    if (ref.current) ref.current.currentTime = event.timestamp;
  };
  return (
    <>
      <Link className="back" to="/videos">
        <ArrowLeft size={16} />
        Video library
      </Link>
      <ErrorBox>{video.error}</ErrorBox>
      {!v ? (
        <Loading />
      ) : (
        <>
          <PageHead
            eyebrow={v.camera_id}
            title={v.filename}
            subtitle={`${clock(v.duration)} · ${v.width} × ${v.height} · ${v.id}`}
          >
            <Badge value={v.status} />
          </PageHead>
          <ErrorBox>{error || v.error}</ErrorBox>
          <div className="detail-grid">
            <div>
              <section className="panel">
                <div className="panel-head">
                  <h2>Footage</h2>
                  {v.has_overlay && (
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={overlay}
                        onChange={(e) => setOverlay(e.target.checked)}
                      />
                      Tracking overlay
                    </label>
                  )}
                </div>
                <VideoPlayer
                  src={`/api/videos/${id}/media?variant=${v.has_overlay && overlay ? "overlay" : v.has_playback ? "playback" : "original"}`}
                  videoRef={ref}
                  onTime={setTime}
                />
              </section>
              {["UPLOADED", "FAILED"].includes(v.status) && (
                <section className="panel padded">
                  <h2>Configure analysis</h2>
                  <p>
                    Define rectangular zones using normalized coordinates (0–1),
                    measured from the top-left of the video. Tracking records
                    neutral zone entries and exits.
                  </p>
                  <div className="zone-preview">
                    {zones.map((z, i) => (
                      <div
                        key={i}
                        style={{
                          left: `${z.x1 * 100}%`,
                          top: `${z.y1 * 100}%`,
                          width: `${Math.max(0, z.x2 - z.x1) * 100}%`,
                          height: `${Math.max(0, z.y2 - z.y1) * 100}%`,
                        }}
                      >
                        {z.name}
                      </div>
                    ))}
                    <span>Frame coordinate preview</span>
                  </div>
                  {zones.map((z, i) => (
                    <div className="zone-row" key={i}>
                      <label>
                        Name
                        <input
                          value={z.name}
                          onChange={(e) =>
                            zoneChange(i, "name", e.target.value)
                          }
                        />
                      </label>
                      {["x1", "y1", "x2", "y2"].map((k) => (
                        <label key={k}>
                          {k}
                          <input
                            type="number"
                            step="0.05"
                            min="0"
                            max="1"
                            value={z[k]}
                            onChange={(e) => zoneChange(i, k, e.target.value)}
                          />
                        </label>
                      ))}
                      <button
                        aria-label="Remove zone"
                        onClick={() =>
                          setZones(zones.filter((_, n) => n !== i))
                        }
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                  <button
                    disabled={zones.length >= 10}
                    className="secondary"
                    onClick={() =>
                      setZones([
                        ...zones,
                        {
                          name: `zone_${zones.length + 1}`,
                          x1: 0.2,
                          y1: 0.2,
                          x2: 0.8,
                          y2: 0.8,
                        },
                      ])
                    }
                  >
                    <Plus size={15} />
                    Add zone
                  </button>
                  <div className="process-actions">
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={detect && !!config.data?.cv_enabled}
                        disabled={!config.data?.cv_enabled}
                        onChange={(e) => setDetect(e.target.checked)}
                      />
                      YOLO person tracking{" "}
                      {config.data &&
                        !config.data.cv_enabled &&
                        "(disabled on server)"}
                    </label>
                    <button
                      className="primary"
                      onClick={process}
                      disabled={busy || !config.data}
                    >
                      <ScanLine size={16} />
                      Start processing
                    </button>
                  </div>
                  <p className="muted">
                    Without tracking, the worker converts footage for browser
                    playback. Completed analysis is immutable.
                  </p>
                </section>
              )}
              {["QUEUED", "PROCESSING", "ANALYZING"].includes(v.status) && (
                <section className="panel padded">
                  <h2>
                    {human(v.status)} · {v.progress}%
                  </h2>
                  <progress max="100" value={v.progress} />
                  <p>
                    Processing runs in the background. You can leave this page.
                  </p>
                </section>
              )}
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Observation timeline</h2>
                    <p>
                      {events.data?.total || 0} zone entries and exits · not
                      incident determinations
                    </p>
                  </div>
                </div>
                <ErrorBox>{events.error}</ErrorBox>
                {events.data?.items.length ? (
                  <div className="timeline">
                    {events.data.items.map((event) => (
                      <button key={event.id} onClick={() => seek(event)}>
                        <span className="mono">{clock(event.timestamp)}</span>
                        <span>
                          <strong>{human(event.event_type)}</strong>
                          <small>
                            {event.zone} · P{event.track_id}
                          </small>
                        </span>
                        <Play size={14} />
                      </button>
                    ))}
                  </div>
                ) : (
                  <Empty title="No zone observations">
                    Add zones and enable tracking before processing. Events
                    appear only when a tracked person crosses a configured zone.
                  </Empty>
                )}
                <Pager
                  page={eventPage}
                  total={events.data?.total || 0}
                  size={100}
                  onChange={setEventPage}
                />
              </section>
            </div>
            <aside>
              <section className="panel padded sticky">
                <span className="eyebrow">HUMAN REVIEW</span>
                <h2>Document an incident</h2>
                <p>Create a case based on your review of the footage.</p>
                {v.status !== "COMPLETED" ? (
                  <div className="notice">
                    Complete processing to create incidents and evidence clips.
                  </div>
                ) : (
                  <form onSubmit={create} className="stack">
                    <label>
                      Timestamp (seconds)
                      <input
                        type="number"
                        name="timestamp"
                        step="0.1"
                        min="0"
                        max={Math.max(0, v.duration - 0.01)}
                        value={Math.round(time * 10) / 10}
                        onChange={(e) => {
                          setTime(Number(e.target.value));
                          setSelectedEvent(null);
                        }}
                        required
                      />
                    </label>
                    {selectedEvent && (
                      <small>Linked observation: {selectedEvent}</small>
                    )}
                    <label>
                      Category
                      <select name="category">
                        <option value="other">Other observation</option>
                        <option value="zone_transition">Zone transition</option>
                        <option value="checkout_anomaly">
                          Checkout review
                        </option>
                        <option value="item_handling">Item handling</option>
                        <option value="possible_scan_mismatch">
                          Possible scan mismatch (human assessment)
                        </option>
                      </select>
                    </label>
                    <label>
                      Review priority
                      <select name="priority">
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                        <option value="high">High</option>
                      </select>
                    </label>
                    <label>
                      Your observations
                      <textarea
                        name="notes"
                        rows="5"
                        minLength="1"
                        maxLength="5000"
                        required
                        placeholder="Describe the observable sequence and what needs review."
                      />
                    </label>
                    <button className="primary" disabled={busy}>
                      <Plus size={16} />
                      Create incident
                    </button>
                    <small>
                      A clip covering up to 10 seconds before and after your
                      timestamp will be generated.
                    </small>
                  </form>
                )}
              </section>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
