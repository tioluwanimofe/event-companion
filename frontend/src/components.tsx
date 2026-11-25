// Small pieces used by more than one page.
import { signInUrl } from "./api";

/** Shown on pages that need you to be signed in. `next` brings you back after Google. */
export function SignInPrompt({ next, why }: { next: string; why: string }) {
  return (
    <main className="page">
      <h1>Sign in first</h1>
      <p>{why}</p>
      <a className="button button--big" href={signInUrl(next)}>Sign in with Google</a>
    </main>
  );
}
