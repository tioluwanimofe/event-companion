// Home: who you are, and your "passport" of booths you've shared with.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, signInUrl } from "../api";
import { friendlyTime } from "../format";
import { keys, useMe } from "../queries";

export default function HomePage() {
  const me = useMe();
  const queryClient = useQueryClient();
  const visits = useQuery({ queryKey: keys.visits, queryFn: api.myVisits, enabled: !!me.data });

  if (me.isPending) return <main className="page"><p role="status">Loading…</p></main>;
  if (me.isError) return <main className="page"><p className="note note--problem">{me.error.message}</p></main>;

  if (!me.data) {
    return (
      <main className="page">
        <h1>Event Companion</h1>
        <p>Scan a booth's QR code with your phone camera, or sign in to see your booth visits.</p>
        <a className="button button--big" href={signInUrl("/")}>Sign in with Google</a>
      </main>
    );
  }

  async function signOut() {
    await api.logout();
    queryClient.clear(); // forget everything we fetched as this person
    queryClient.setQueryData(keys.me, null);
  }

  return (
    <main className="page">
      <header className="page__header">
        <h1>Hi, {me.data.first_name}</h1>
        <button className="button button--quiet" onClick={signOut}>Sign out</button>
      </header>
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
