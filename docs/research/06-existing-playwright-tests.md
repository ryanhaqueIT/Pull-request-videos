# Existing Playwright E2E Tests — AWS-Hackathon

## Location

`C:\Users\drnaz\Ryan\AWS-Hackathon\tests\e2e\`

## Test Specs (8 Journeys)

| Spec File | Journey | What It Tests |
|-----------|---------|---------------|
| `j1-registration-login.spec.ts` | J1 | Root redirect, login page, signup, registration, login flow |
| `j2-profile-setup.spec.ts` | J2 | Profile setup page, URL chips, textarea, file upload, preview panel, workspace tabs (SOUL.md, Principles.md) |
| `j3-new-leads.spec.ts` | J3 | New Leads page, empty state, sidebar navigation |
| `j4-existing-leads.spec.ts` | J4 | Existing leads display |
| `j5-settings.spec.ts` | J5 | Settings page |
| `j6-auth-protection.spec.ts` | J6 | Auth protection on routes |
| `j7-logout.spec.ts` | J7 | Logout flow |
| `j8-login-refresh-race.spec.ts` | J8 | Login refresh race condition |

## Current Config

```typescript
// playwright.config.ts
{
  video: "retain-on-failure",    // Only records on failures
  screenshot: "only-on-failure",
  trace: "retain-on-failure",
  baseURL: "http://localhost:3001",
  workers: 1,                    // Serial execution
  timeout: 60_000,
}
```

## Screenshot Evidence

Already captures milestone screenshots at:
`C:/Users/ryanh/AWS-BB/tests/e2e/screenshots/`

Examples: `j1-01-root-redirects-to-login.png`, `j2-01-setup-page-loaded.png`, etc.

## Recording Config Created

A new `playwright.record.config.ts` has been created that:
- Sets `video: "on"` (always record)
- Uses `slowMo: 300` (human-readable pacing)
- Viewport: 1280x720 (clean 720p)
- Output: `./demo-recordings/`

## Conversion Scripts Created

- `scripts/convert-videos.mjs` — Node.js script to convert WebM → MP4 + GIF
- `scripts/videos-to-gif.sh` — Bash script (requires ffmpeg)
- `scripts/record-demo.sh` — One-command: run tests + convert

## Usage

```bash
# Record all journeys
npx playwright test --config=playwright.record.config.ts

# Record specific journey
npx playwright test --config=playwright.record.config.ts --grep "j2"

# Convert to GIF
node scripts/convert-videos.mjs demo-recordings demo-gifs
```
