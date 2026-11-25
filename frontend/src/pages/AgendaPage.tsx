// /events/:slug/agenda: the schedule. Public, no sign-in needed.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { api } from "../api";
import { groupAgenda, matchesTrack, timeIn, timing, tracksOf, zoneLabel } from "../agenda";
import { keys } from "../queries";
import type { AgendaSession } from "../types";
import "./AgendaPage.css";

const KIND_LABEL: Partial<Record<AgendaSession["kind"], string>> = {
  keynote: "Keynote", panel: "Panel", meal: "Meal", networking: "Networking",
};

/** The current time, ticking once a minute so "Happening now" stays true. */
function useNow(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(timer); // 🧠 clean up, or every visit leaves a timer running
  }, []);
  return now;
}

export default function AgendaPage() {
  const { slug = "" } = useParams();
  const now = useNow();
  const [track, setTrack] = useState<string | null>(null);
  // Re-check every 5 minutes: organizers do move rooms on the day.
  const agenda = useQuery({ queryKey: keys.agenda(slug), queryFn: () => api.agenda(slug), refetchInterval: 300_000 });

  if (agenda.isPending) return <main className="page"><p role="status">Loading the agenda…</p></main>;
  if (agenda.isError) {
    return (
      <main className="page">
        <Link className="back" to="/">← Home</Link>
        <p className="note note--problem" role="alert">{agenda.error.message}</p>
      </main>
    );
  }

  const { event_name, timezone, sessions } = agenda.data;
  const tracks = tracksOf(sessions);
  const days = groupAgenda(sessions.filter((s) => matchesTrack(s, track)), timezone);

  return (
    <main className="page agenda">
      <Link className="back" to="/">← Home</Link>
      <h1>{event_name}</h1>
      {sessions.length > 0 && (
        <p className="fineprint">All times are {zoneLabel(sessions[0].starts_at, timezone)}, the event's local time.</p>
      )}

      {tracks.length > 1 && (
        <div className="chips" role="group" aria-label="Filter by track">
          {[null, ...tracks].map((t) => (
            <button key={t ?? "all"} className="chip" aria-pressed={track === t} onClick={() => setTrack(t)}>
              {t ?? "All"}
            </button>
          ))}
        </div>
      )}

      {sessions.length === 0 && <p className="fineprint">The agenda hasn't been posted yet. Check back soon.</p>}

      {days.map((day) => (
        <section key={day.day} className="agenda__day">
          {days.length > 1 && <h2>{day.day}</h2>}
          {day.slots.map((slot) => (
            <div key={slot.start} className="slot">
              <p className="slot__time">{slot.start}</p>
              <div className="slot__sessions">
                {slot.sessions.map((s) => <SessionCard key={s.id} session={s} timeZone={timezone} now={now} />)}
              </div>
            </div>
          ))}
        </section>
      ))}
    </main>
  );
}

function SessionCard({ session: s, timeZone, now }: { session: AgendaSession; timeZone: string; now: Date }) {
  const when = timing(s, now);
  const where = [s.room, s.building].filter(Boolean).join(", ");
  return (
    <article className={`card session session--${s.kind} session--${when}`}>
      <div className="session__top">
        <span className="fineprint">{timeIn(s.starts_at, timeZone)} – {timeIn(s.ends_at, timeZone)}</span>
        {when === "now" && <span className="badge badge--now">Happening now</span>}
        {KIND_LABEL[s.kind] && <span className="badge">{KIND_LABEL[s.kind]}</span>}
      </div>
      <h3>{s.title}</h3>
      {where && <p className="where session__where">{where}</p>}
      {s.speakers.length > 0 && (
        <p className="session__speakers">
          {s.speakers.map((p) => (p.company ? `${p.name} (${p.company})` : p.name)).join(", ")}
        </p>
      )}
      {s.track && <p className="fineprint">{s.track}</p>}
      {s.description && (
        <details>
          <summary>About this session</summary>
          <p className="notes__body">{s.description}</p>
        </details>
      )}
    </article>
  );
}
