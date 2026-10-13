# astro-door
Login → Pay (Razorpay) → App, with a private local admin.

- `site/`  the public website (Vercel Root Directory = `site`)
- `admin/admin.html`  open from your own computer, never host it
- `functions/`  Supabase Edge Functions (already deployed; source kept here)
- `tests/`  mocked end-to-end tests (Playwright)
