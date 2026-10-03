import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronRight,
  Film,
  RotateCcw,
  FastForward,
  Play,
  Inbox,
} from "lucide-react";
import { api, errorText, human, clock } from "./api";

export function useData(path, interval = 0) {
  const [data, setData] = useState(null),
    [error, setError] = useState("");
  const reload = async () => {
    try {
      const r = await api.get(path);
      setData(r.data);
      setError("");
      return r.data;
    } catch (e) {
      setError(errorText(e));
    }
  };
  useEffect(() => {
    let alive = true;
    const read = async () => {
      try {
        const r = await api.get(path);
        if (alive) {
          setData(r.data);
          setError("");
        }
      } catch (e) {
        if (alive) setError(errorText(e));
      }
    };
    setData(null);
    read();
    const t = interval ? setInterval(read, interval) : null;
    return () => {
      alive = false;
      if (t) clearInterval(t);
    };
  }, [path, interval]);
  return { data, error, reload };
}
export const ErrorBox = ({ children }) =>
  children ? (
    <div role="alert" className="error">
      {children}
    </div>
  ) : null;
export const Badge = ({ value }) => (
  <span className={`badge ${String(value).toLowerCase()}`}>{human(value)}</span>
);
export const Loading = () => (
  <div className="empty">
    <div className="spinner" />
    Loading workspace…
  </div>
);
export function Empty({ title = "Nothing here yet", children }) {
  return (
    <div className="empty">
      <Inbox size={32} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function PageHead({ eyebrow = "WORKSPACE", title, subtitle, children }) {
  return (
    <header className="page-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div>{children}</div>
    </header>
  );
}
export function Metrics({ data }) {
  return (
    <div className="metrics">
      {[
        ["Videos processed", data.processed, "Ready to review"],
        ["Zone observations", data.events, "Neutral movement events"],
        [
          "Open incidents",
          data.incidents - data.resolved,
          "Human-created cases",
        ],
        ["Resolution rate", `${data.resolution_rate}%`, "Of visible incidents"],
      ].map(([label, value, note]) => (
        <div className="metric" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
          <small>{note}</small>
        </div>
      ))}
    </div>
  );
}
export function IncidentTable({ items }) {
  return items?.length ? (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Incident / camera</th>
            <th>Category</th>
            <th>Timestamp</th>
            <th>Priority</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.id}>
              <td>
                <Link className="table-link" to={`/incidents/${i.id}`}>
                  {i.id.slice(0, 12)}
                </Link>
                <small>{i.camera_id}</small>
              </td>
              <td className="capitalize">{human(i.category)}</td>
              <td className="mono">{clock(i.timestamp)}</td>
              <td>
                <Badge value={i.priority} />
              </td>
              <td>
                <Badge value={i.status} />
              </td>
              <td>
                <Link aria-label={`Open ${i.id}`} to={`/incidents/${i.id}`}>
                  <ChevronRight size={18} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty title="Your queue is clear">
      Create an incident from a processed video when you want to document a
      review.
    </Empty>
  );
}
export function Pager({ page, total, size, onChange }) {
  return total > size ? (
    <div className="pager">
      <button disabled={page === 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} / {Math.ceil(total / size)}
      </span>
      <button
        disabled={page * size >= total}
        onClick={() => onChange(page + 1)}
      >
        Next
      </button>
    </div>
  ) : null;
}
export function VideoPlayer({ src, eventTime = 0, onTime, videoRef }) {
  const own = useRef(),
    ref = videoRef || own;
  const [error, setError] = useState("");
  useEffect(() => setError(""), [src]);
  const seek = (s) => {
    if (ref.current)
      ref.current.currentTime = Math.max(
        0,
        Math.min(
          Number.isFinite(ref.current.duration) ? ref.current.duration : s,
          s,
        ),
      );
  };
  return (
    <div className="player">
      <video
        ref={ref}
        key={src}
        src={src}
        controls
        preload="metadata"
        onError={() =>
          setError(
            "This video is not ready or cannot be played. Try the processed version.",
          )
        }
        onTimeUpdate={() => onTime?.(ref.current.currentTime)}
      />
      <div className="player-controls">
        <button onClick={() => seek((ref.current?.currentTime || 0) - 10)}>
          <RotateCcw size={15} />
          10 sec
        </button>
        <button onClick={() => seek(eventTime)}>
          <Play size={14} />
          Event {clock(eventTime)}
        </button>
        <button onClick={() => seek((ref.current?.currentTime || 0) + 10)}>
          10 sec
          <FastForward size={15} />
        </button>
        <select
          aria-label="Playback speed"
          onChange={(e) => {
            ref.current.playbackRate = Number(e.target.value);
          }}
          defaultValue="1"
        >
          <option value="0.5">0.5×</option>
          <option value="1">1×</option>
          <option value="1.5">1.5×</option>
          <option value="2">2×</option>
        </select>
      </div>
      <ErrorBox>{error}</ErrorBox>
    </div>
  );
}
