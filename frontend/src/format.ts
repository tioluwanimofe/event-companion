/** "10:42 AM" today, or "Apr 16, 10:42 AM" on another day. In the phone's own time zone. */
export function friendlyTime(iso: string, now: Date = new Date()): string {
  const when = new Date(iso);
  const sameDay = when.toDateString() === now.toDateString();
  return when.toLocaleString(undefined, sameDay
    ? { hour: "numeric", minute: "2-digit" }
    : { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
