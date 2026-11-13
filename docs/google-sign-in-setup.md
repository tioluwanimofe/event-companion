# Setting up Google sign-in (one time, about 10 minutes)

Google only lets an app use "Sign in with Google" once it's registered. You do that once, by
clicking, in Google Cloud Console. It's free. At the end you'll have two values, a **Client ID**
and a **Client secret**, and you paste them into `backend/.env`.

Why this design: [ADR 0004](decisions/0004-google-sign-in.md).

## 1. Create a Google Cloud project

1. Go to <https://console.cloud.google.com/> and sign in with your Google account.
2. At the top, click the project picker → **New project**. Name it `Event Companion` → **Create**.
3. Make sure the new project is selected in the picker.

## 2. Set up the consent screen (what people see when they sign in)

1. In the search bar, type **Google Auth Platform** and open it (older consoles call this
   **OAuth consent screen**). Click **Get started**.
2. **App name:** `Event Companion`. **User support email:** your email. → **Next**.
3. **Audience:** choose **External** (attendees use regular Google accounts). → **Next**.
4. **Contact information:** your email. → **Next** → agree → **Create**.
5. Open **Audience** → under **Test users**, click **Add users** and add your own Gmail
   (and anyone else who'll test it). While the app is in "Testing" mode, only test users can sign in.
   That's exactly what we want for now.

## 3. Create the OAuth client (the two values)

1. Open **Clients** → **Create client**.
2. **Application type:** **Web application**. **Name:** `Event Companion local`.
3. Under **Authorized redirect URIs**, click **Add URI** and add **both** of these exactly:
   - `http://127.0.0.1:8000/auth/google/callback`
   - `http://localhost:8000/auth/google/callback`
4. Click **Create**. A box shows your **Client ID** and **Client secret**. Copy both now.

> 🧠 **Why the redirect URI matters:** after you sign in, Google sends you back *only* to an address on
> this list. That stops another site from receiving your sign-in. A typo here gives a
> `redirect_uri_mismatch` error.

## 4. Put the values in `backend/.env`

Open `backend/.env` in VS Code and add these lines (see `.env.example`):

```
GOOGLE_CLIENT_ID=paste-the-client-id-here
GOOGLE_CLIENT_SECRET=paste-the-client-secret-here
SESSION_SECRET_KEY=paste-a-random-key-here
ADMIN_EMAILS=your.gmail@gmail.com
```

For `SESSION_SECRET_KEY`, run **Terminal → Run Task… → 5. Make a secret key** and paste what it prints.
Save with **Ctrl+S**. `.env` is ignored by Git, so these never go to GitHub.

## 5. Try it

1. **Run Task → 1. Install / update Python packages** (two new packages), then **3. Start the API**.
2. In your browser, open **<http://127.0.0.1:8000/auth/google/login>**. Use the address bar, not
   "Try it out" in `/docs`.
3. Pick your Google account. You land back on `/docs`, signed in.
4. In `/docs`, try **GET /auth/me** → you, with `"is_platform_admin": true`.
5. Try any `/admin` endpoint: it works. Open a private/incognito window and try the same one: **401**.

Use the same address every time (`127.0.0.1` *or* `localhost`, not a mix). The browser treats them as
two different sites, with separate cookies.

## When it goes online

Add the real address (for example `https://api.cyberdatacon.com/auth/google/callback`) to the
redirect URIs, set `SESSION_COOKIE_SECURE=true`, and publish the consent screen so anyone with a
Google account can sign in.
