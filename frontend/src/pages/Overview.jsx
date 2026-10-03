import React from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Upload, Download, ShieldCheck } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  useData,
  PageHead,
  Metrics,
  IncidentTable,
  Loading,
  ErrorBox,
  Empty,
} from "../components";
import { human } from "../api";
const palette = ["#277b64", "#9cc6b0", "#d4ac61", "#8b9eac", "#d5ded7"];
function Chart({ items, type = "bar" }) {
  return items?.length ? (
    <ResponsiveContainer width="100%" height={240}>
      {type === "pie" ? (
        <PieChart>
          <Pie
            isAnimationActive={false}
            data={items}
            dataKey="count"
            nameKey="name"
            innerRadius={64}
            outerRadius={90}
            paddingAngle={4}
          >
            {items.map((_, i) => (
              <Cell key={i} fill={palette[i % palette.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v, n) => [v, human(n)]} />
        </PieChart>
      ) : (
        <BarChart
          data={items}
          margin={{ top: 10, right: 10, left: -25, bottom: 15 }}
        >
          <CartesianGrid vertical={false} stroke="#e9ede8" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10 }}
            tickFormatter={(s) => (s.length > 12 ? s.slice(-5) : s)}
          />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar
            isAnimationActive={false}
            dataKey="count"
            fill="#348c70"
            radius={[5, 5, 0, 0]}
            maxBarSize={35}
          />
        </BarChart>
      )}
    </ResponsiveContainer>
  ) : (
    <Empty title="Awaiting your first review">
      Charts update from actual workspace records.
    </Empty>
  );
}
export function Dashboard({ user }) {
  const summary = useData("/analytics/summary", 5000),
    queue = useData("/incidents?status=NEEDS_REVIEW", 5000);
  return (
    <>
      <PageHead
        eyebrow="YOUR OPERATIONS, AT A GLANCE"
        title={`Good to see you, ${user.name.split(" ")[0]}.`}
        subtitle="A focused view of footage and cases that need a human decision."
      >
        <Link className="primary" to="/videos">
          <Upload size={17} />
          Upload video
        </Link>
      </PageHead>
      <ErrorBox>{summary.error || queue.error}</ErrorBox>
      {!summary.data ? (
        <Loading />
      ) : (
        <>
          <Metrics data={summary.data} />
          <div className="overview-grid">
            <section className="panel">
              <div className="panel-head">
                <div>
                  <h2>Incident activity</h2>
                  <p>Human-created incidents by day</p>
                </div>
                <span className="subtle">All recorded days</span>
              </div>
              <Chart items={summary.data.days} />
            </section>
            <section className="panel review-principle">
              <span className="eyebrow">A CLEARER REVIEW PROCESS</span>
              <ShieldCheck size={40} />
              <h2>Context before conclusions.</h2>
              <p>
                Review the full sequence, document your observations, and keep
                each decision connected to its evidence.
              </p>
              <Link to="/incidents">
                Open incident queue
                <ArrowUpRight size={18} />
              </Link>
            </section>
          </div>
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>
                  Ready for review{" "}
                  <span className="count">{queue.data?.total || 0}</span>
                </h2>
                <p>Your latest cases awaiting a decision</p>
              </div>
              <Link to="/incidents" className="text-link">
                View all
                <ArrowUpRight size={16} />
              </Link>
            </div>
            <IncidentTable items={queue.data?.items?.slice(0, 5)} />
          </section>
        </>
      )}
    </>
  );
}
export function Analytics() {
  const { data, error } = useData("/analytics/summary", 5000);
  return (
    <>
      <PageHead
        title="Operational analytics"
        subtitle="Review outcomes and turnaround from your accessible records."
      />
      <ErrorBox>{error}</ErrorBox>
      {data ? (
        <>
          <Metrics data={data} />
          <div className="analytics-strip">
            <div>
              <strong>{data.reviewed}</strong>
              <span>Cases with a review</span>
            </div>
            <div>
              <strong>{data.escalated}</strong>
              <span>Escalated by reviewers</span>
            </div>
            <div>
              <strong>{data.average_first_review_minutes ?? "—"}</strong>
              <span>Avg. minutes to first review</span>
            </div>
          </div>
          <div className="two-columns">
            {[
              ["Incidents over time", data.days],
              ["Review outcomes", data.outcomes, "pie"],
              ["Categories", data.categories],
              ["Store activity", data.stores],
            ].map(([title, items, type]) => (
              <section className="panel" key={title}>
                <div className="panel-head">
                  <h2>{title}</h2>
                </div>
                <Chart items={items} type={type} />
                {type === "pie" && (
                  <div className="legend">
                    {items.map((x, i) => (
                      <span key={x.name}>
                        <i
                          style={{ background: palette[i % palette.length] }}
                        />
                        {human(x.name)} · {x.count}
                      </span>
                    ))}
                  </div>
                )}
              </section>
            ))}
          </div>
          <p className="muted">
            Outcomes reflect reviewer decisions, not model accuracy. Turnaround
            is elapsed time from case creation to first submitted review.
          </p>
        </>
      ) : (
        <Loading />
      )}
    </>
  );
}
export function Reports() {
  return (
    <>
      <PageHead
        title="Reports & exports"
        subtitle="Take your review records into reporting and business intelligence."
      />
      <div className="two-columns">
        <section className="panel padded">
          <Download className="feature-icon" />
          <h2>Incident dataset</h2>
          <p>
            Export accessible incidents, decisions, timestamps, and notes. Ready
            for Excel, Python, or Power BI.
          </p>
          <a href="/api/reports/incidents.csv" className="primary">
            Download CSV
            <Download size={16} />
          </a>
        </section>
        <section className="panel padded">
          <ShieldCheck className="feature-icon" />
          <h2>Investigation reports</h2>
          <p>
            Each case has a PDF and JSON report with evidence references and an
            embedded decision history.
          </p>
          <Link to="/incidents" className="secondary">
            Choose an incident
            <ArrowUpRight size={16} />
          </Link>
        </section>
      </div>
      <section className="panel padded">
        <h2>Power BI workflow</h2>
        <ol className="steps">
          <li>Download the incident CSV.</li>
          <li>In Power BI Desktop, choose Get Data → Text/CSV.</li>
          <li>
            Use the included analytics/power-bi.md measures for review
            completion, escalation, and store trends.
          </li>
        </ol>
        <p className="muted">
          Exports contain review notes. Share them only with the appropriate
          investigation team.
        </p>
      </section>
    </>
  );
}
export function Investigations() {
  const { data, error } = useData("/investigations");
  return (
    <>
      <PageHead
        title="Review history"
        subtitle="Most recently reviewed cases, with every decision preserved."
      />
      <ErrorBox>{error}</ErrorBox>
      <section className="panel">
        {data ? <IncidentTable items={data} /> : <Loading />}
      </section>
    </>
  );
}
