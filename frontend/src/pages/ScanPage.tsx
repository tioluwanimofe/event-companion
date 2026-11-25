// The first screen of the app: what the phone camera opens from a booth's QR code.
//
//   /scan/:token  →  1. which booth is this?            GET  /api/scan/{token}
//                    2. sign in (if needed)              /api/auth/google/login?next=/scan/{token}
//                    3. tap "Share my profile"           POST /api/scan/{token}
//                    4. see the booth's notes
//
// 🧠 Opening this page shares NOTHING (Tio's one-tap consent rule, 2026-11-18).
// Only the button does, and only the button's POST makes the person a lead.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { api, ApiError, signInUrl } from "../api";
import { friendlyTime } from "../format";
import { keys } from "../queries";
import type { ScanResult } from "../types";
import "./ScanPage.css";

export default function ScanPage() {
  const { token = "" } = useParams();
  const queryClient = useQueryClient();

  const preview = useQuery({ queryKey: keys.scan(token), queryFn: () => api.scanPreview(token) });

  const share = useMutation({
    mutationFn: () => api.shareWithBooth(token),
    onSuccess: () => {
      // The passport list and this booth's "already shared" line are now out of date.
      queryClient.invalidateQueries({ queryKey: keys.visits });
      queryClient.invalidateQueries({ queryKey: keys.scan(token) });
    },
  });

  if (preview.isPending) {
    return <main className="scan"><p className="scan__status" role="status">Finding the booth…</p></main>;
  }
  if (preview.isError) {
    return (
      <main className="scan">
        <section className="card card--problem">
          <h1>Hmm, that code didn't work</h1>
          <p>{preview.error.message}</p>
          {!(preview.error instanceof ApiError && preview.error.status === 404) && (
            <button className="button" onClick={() => preview.refetch()}>Try again</button>
          )}
        </section>
      </main>
    );
  }

  const booth = preview.data;
  if (share.isSuccess) return <Shared result={share.data} />;

  return (
    <main className="scan">
      <p className="scan__event">{booth.event_name}</p>
      <section className="card">
        <p className="eyebrow">You scanned</p>
        <h1 className="scan__booth">{booth.booth_name}</h1>
        {booth.location_label && <p className="scan__where">{booth.location_label}</p>}
        {booth.description && <p className="scan__about">{booth.description}</p>}
      </section>

      {booth.already_shared_at && (
        <p className="note note--ok">
          ✓ You shared your profile with this booth at {friendlyTime(booth.already_shared_at)}.
        </p>
      )}

      <section className="consent">
        <h2>{booth.already_shared_at ? "Their notes for you" : `Share your profile with ${booth.booth_name}?`}</h2>
        {!booth.already_shared_at && (
          <p>
            They'll see your <strong>name, email</strong>, and the company, job title or school
            from your registration. In return you get their notes and links.
          </p>
        )}

        {share.isError && <p className="note note--problem" role="alert">{share.error.message}</p>}

        {booth.signed_in ? (
          <button className="button button--big" onClick={() => share.mutate()} disabled={share.isPending}>
            {share.isPending ? "Sharing…" : booth.already_shared_at ? "Show their notes" : "Share my profile"}
          </button>
        ) : (
          // A real link, not fetch(): sign-in leaves the app, visits Google, and comes back here.
          <a className="button button--big" href={signInUrl(`/scan/${token}`)}>
            Sign in with Google to share
          </a>
        )}
        {!booth.already_shared_at && <p className="fineprint">Nothing is shared until you tap the button.</p>}
      </section>
    </main>
  );
}

function Shared({ result }: { result: ScanResult }) {
  return (
    <main className="scan">
      <section className="card card--ok" aria-live="polite">
        <p className="stamp">✓ {result.first_time ? "Shared" : "Already shared"}</p>
        <h1 className="scan__booth">{result.booth_name}</h1>
        {result.location_label && <p className="scan__where">{result.location_label}</p>}
        <p className="fineprint">at {friendlyTime(result.shared_at)}</p>
      </section>
      <section className="notes">
        <h2>Notes from {result.booth_name}</h2>
        {/* React escapes this text, so a booth can't inject HTML or scripts into your phone. */}
        {result.preloaded_notes
          ? <p className="notes__body">{result.preloaded_notes}</p>
          : <p className="fineprint">This booth hasn't added notes yet.</p>}
      </section>
      <Link className="button button--quiet" to="/">See all my booth visits</Link>
    </main>
  );
}
