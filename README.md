# astro-door
Login → Pay (Razorpay) → App, with a private local admin.

- `index.html`, `legal.html`, `vercel.json`  the public website (Vercel serves the repo root, no settings needed)
- `admin/admin.html`  open from your own computer, never share it (blocked on the website by vercel.json)
- `functions/`  Supabase Edge Functions (already deployed; source kept here)
- `tests/`  mocked end-to-end tests (Playwright)
