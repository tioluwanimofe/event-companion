// /my-booths/:boothId: everyone who tapped "Share my profile" at this booth.
// Booth staff keep this open during the event, so it refreshes itself.
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { api, leadsCsvUrl } from "../api";
import { SignInPrompt } from "../components";
import { friendlyTime } from "../format";
import { keys, useMe, useMyBooths } from "../queries";
import type { Lead } from "../types";

const REFRESH_EVERY_MS = 30_000;

export default function BoothLeadsPage() {
  const { boothId = "" } = useParams();
  const me = useMe();
  const signedIn = !!me.data;
  const booths = useMyBooths(signedIn);
  // 🧠 refetchInterval: TanStack Query asks again every 30 s while this page is open,
  // so new leads appear without anyone pressing refresh. It pauses when the tab is hidden.
  const leads = useQuery({
    queryKey: keys.leads(boothId),
    queryFn: () => api.boothLeads(boothId),
    enabled: signedIn,
    refetchInterval: REFRESH_EVERY_MS,
  });

  if (me.isPending) return <main className="page"><p role="status">Loading…</p></main>;
  if (!signedIn) return <SignInPrompt next={`/my-booths/${boothId}`} why="Sign in to see your booth's leads." />;

  // Event admins can open any booth's leads but don't "run" it, so the name may not be in this list.
  const booth = booths.data?.find((b) => b.id === boothId);

  return (
    <main className="page">
      <Link className="back" to="/my-booths">← My booths</Link>
      <h1>{booth?.name ?? "Booth leads"}</h1>
      {booth?.location_label && <p className="where">{booth.location_label}</p>}

      {leads.isError ? (
        <p className="note note--problem" role="alert">{leads.error.message}</p>
      ) : (
        <>
          <div className="leads-bar">
            <p className="leads-bar__count">
              <strong>{leads.data?.length ?? "…"}</strong> {leads.data?.length === 1 ? "person" : "people"} shared with you
            </p>
            <a className="button" href={leadsCsvUrl(boothId)} download>Download spreadsheet</a>
          </div>
          <p className="fineprint">
            {leads.isFetching
              ? "Checking for new leads…"
              : leads.dataUpdatedAt > 0 &&
                `Updated ${friendlyTime(new Date(leads.dataUpdatedAt).toISOString())}. Refreshes every 30 seconds.`}
          </p>
          {leads.data?.length === 0 && (
            <p className="fineprint">No leads yet. When someone scans your QR code and taps "Share my profile", they'll show up here.</p>
          )}
          <ul className="visits">
            {leads.data?.map((lead) => <LeadCard key={`${lead.email}-${lead.shared_at}`} lead={lead} />)}
          </ul>
        </>
      )}
    </main>
  );
}

/** "Security Analyst at Acme" or "Student · Lipscomb University · Computer Science" */
export function leadSubtitle(lead: Lead): string {
  if (lead.is_student) return ["Student", lead.university, lead.major].filter(Boolean).join(" · ");
  if (lead.job_title && lead.company) return `${lead.job_title} at ${lead.company}`;
  return lead.job_title ?? lead.company ?? "";
}

function LeadCard({ lead }: { lead: Lead }) {
  const subtitle = leadSubtitle(lead);
  return (
    <li className="card lead">
      <div className="lead__top">
        <h3>{lead.first_name} {lead.last_name}</h3>
        <span className="fineprint">{friendlyTime(lead.shared_at)}</span>
      </div>
      {subtitle && <p className="lead__sub">{subtitle}</p>}
      <a className="lead__email" href={`mailto:${lead.email}`}>{lead.email}</a>
    </li>
  );
}
