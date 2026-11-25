// Home: who you are, and your "passport" of booths you've shared with.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { api, signInUrl } from "../api";
import { friendlyTime } from "../format";
import { keys, useMe, useMyBooths } from "../queries";

// The event the signed-out home page points at (set VITE_EVENT_SLUG in frontend/.env).
const DEFAULT_EVENT = import.meta.env.VITE_EVENT_SLUG as string | undefined;

function AgendaLink({ slug }: { slug: string }) {
  return <Link className="button button--quiet agenda-link" to={`/events/${slug}/agenda`}>📅 Agenda{slug !== DEFAULT_EVENT ? `: ${slug}` : ""}</Link>;
}

export default function HomePage() {
  const me = useMe();
  const queryClient = useQueryClient();
  const visits = useQuery({ queryKey: keys.visits, queryFn: api.myVisits, enabled: !!me.data });
  const myBooths = useMyBooths(!!me.data);

  if (me.isPending) return <main className="page"><p role="status">Loading…</p></main>;
  if (me.isError) return <main className="page"><p className="note note--problem">{me.error.message}</p></main>;

  if (!me.data) {
    return (
      <main className="page">
        <h1>Event Companion</h1>
        <p>Scan a booth's QR code with your phone camera, or sign in to see your booth visits.</p>
        <a className="button button--big" href={signInUrl("/")}>Sign in with Google</a>
        {DEFAULT_EVENT && <AgendaLink slug={DEFAULT_EVENT} />}
      </main>
    );
  }

  async function signOut() {
    await api.logout();
    queryClient.clear(); // forget everything we fetched as this person
    queryClient.setQueryData(keys.me, null);
  }

  const myEvents = [...new Set(me.data.roles.map((r) => r.event_slug))];
  if (DEFAULT_EVENT && myEvents.length === 0) myEvents.push(DEFAULT_EVENT);

  return (
    <main className="page">
      <header className="page__header">
        <h1>Hi, {me.data.first_name}</h1>
        <button className="button button--quiet" onClick={signOut}>Sign out</button>
      </header>
      <div className="agenda-links">
        {myEvents.map((slug) => <AgendaLink key={slug} slug={slug} />)}
      </div>
      {!!myBooths.data?.length && (
        <Link className="card booth-row booth-row--owner" to="/my-booths">
          <span>
            <strong className="booth-row__name">Your booth leads</strong>
            <span className="fineprint">You run {myBooths.data.length === 1 ? myBooths.data[0].name : `${myBooths.data.length} booths`}</span>
          </span>
          <span className="count">
            {myBooths.data.reduce((sum, b) => sum + b.lead_count, 0)}<small>leads</small>
          </span>
        </Link>
      )}
      <h2>Booths you've visited</h2>
      {visits.isPending && <p role="status">Loading…</p>}
      {visits.isError && <p className="note note--problem">{visits.error.message}</p>}
      {visits.data?.length === 0 && <p className="fineprint">None yet. Scan a booth's QR code to start.</p>}
      <ul className="visits">
        {visits.data?.map((v) => (
          <li key={`${v.event_slug}-${v.booth_name}`} className="card">
            <h3>{v.booth_name}</h3>
            <p className="fineprint">{[v.location_label, friendlyTime(v.shared_at)].filter(Boolean).join(" · ")}</p>
            {v.preloaded_notes && <p className="notes__body">{v.preloaded_notes}</p>}
          </li>
        ))}
      </ul>
    </main>
  );
}
