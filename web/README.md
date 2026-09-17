# Crypt Master admin console

React 19 + Vite + TypeScript SPA for the admin API in `../app/web/`.

## Local development

```bash
npm install
npm run dev
```

The dev server proxies `/api` and `/v2` to `https://localhost:2053` (see
`vite.config.ts`), so run the backend locally per the root README before
starting this. Point `npm run dev` at a plain-HTTP backend during
development by editing that proxy target and setting `SESSION_COOKIE_SECURE=false`
in the backend's `.env` -- browsers won't set a `Secure` cookie over HTTP.

## Building for production

```bash
npm run build
```

Outputs to `dist/`. Serve it from the same origin as the API (e.g. behind
the same reverse proxy, or have FastAPI serve the built files as static
assets) so session cookies work without needing cross-origin credentials.

## What's here

- `src/api/client.ts` -- typed fetch wrapper + response shapes matching
  `app/web/schemas.py`.
- `src/auth/AuthContext.tsx` -- session state (`/api/auth/whoami`), shared
  across the app.
- `src/crypto/` -- the backup feature's client-side cryptography, entirely
  self-contained (no third-party crypto library):
  - `wordlist.ts` -- the official 2048-word BIP-39 English wordlist,
    fetched verbatim from `bitcoin/bips` (sha256 noted in the file).
  - `bip39.ts` -- mnemonic generation/validation and the standard
    mnemonic-to-seed derivation (PBKDF2-HMAC-SHA512), all via native
    WebCrypto.
  - `backupFile.ts` -- turns the plaintext the server hands back into a
    downloadable AES-256-GCM-encrypted file (key derived from the BIP-39
    seed via HKDF), and back.
- `src/pages/SetupPage.tsx` -- first-run flow: create an empty vault,
  restore a backup, or migrate from a legacy v1 server.
- `src/pages/BackupPage.tsx` -- the export wizard: step-up re-auth, generate
  a fresh 24-word seed, show it once, hide it and require retyping it
  exactly, then a passphrase (entered twice), then encrypt and download.
  The seed and passphrase never leave the browser.
- `src/pages/FirstLoginPage.tsx` / `AccountPage.tsx` -- forced and
  voluntary password-change-plus-OTP-re-enrollment flows.

## Verifying this actually works

This was tested against a real running backend with a headless browser
(Playwright) driving the full flow end to end -- setup, forced first login,
password/OTP rotation, server/secret/ACL CRUD, log entries, and a full
backup export -- and the resulting downloaded file was independently
decrypted (outside the app's own code, with a from-scratch WebCrypto
script) to confirm it round-trips correctly. That test script isn't
committed here since it depends on a live backend + Redis + a real browser;
see the session notes for how to reproduce it.
