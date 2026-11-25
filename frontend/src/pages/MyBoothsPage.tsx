// /my-booths: for exhibitors. Every booth you run, with how many people shared with it.
import { Link } from "react-router";
import { SignInPrompt } from "../components";
import { useMe, useMyBooths } from "../queries";

export default function MyBoothsPage() {
  const me = useMe();
  const booths = useMyBooths(!!me.data);

  if (me.isPending) return <main className="page"><p role="status">Loading…</p></main>;
  if (!me.data) return <SignInPrompt next="/my-booths" why="Sign in to see the leads for your booth." />;

  return (
    <main className="page">
      <Link className="back" to="/">← Home</Link>
      <h1>My booths</h1>
      {booths.isPending && <p role="status">Loading…</p>}
      {booths.isError && <p className="note note--problem">{booths.error.message}</p>}
      {booths.data?.length === 0 && (
        <p className="fineprint">
          You're not listed as running a booth. If you should be, ask the organizers to add your
          email to your booth.
        </p>
      )}
      <ul className="visits">
        {booths.data?.map((b) => (
          <li key={b.id}>
            <Link className="card booth-row" to={`/my-booths/${b.id}`}>
              <span>
                <strong className="booth-row__name">{b.name}</strong>
                {b.location_label && <span className="fineprint">{b.location_label}</span>}
              </span>
              <span className="count" aria-label={`${b.lead_count} leads`}>
                {b.lead_count}<small>{b.lead_count === 1 ? "lead" : "leads"}</small>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
