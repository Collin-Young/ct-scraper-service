# GeoLeads Frontend (React + Shadcn UI)

Modernized UI built with Vite, React, Tailwind, and Shadcn components. The previous static implementation remains in `../frontend-legacy` for reference and staging.

## Prerequisites
- Node.js 18+
- npm, pnpm, or yarn

## Getting Started
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`, set the API base URL (defaults to `https://geoleads.land/api` when hosted), and click **Refresh** to load cases.

## Building for Production
```bash
npm run build
npm run preview
```

Deploy the generated `dist/` folder to static hosting or your existing deployment pipeline.

---
Need to roll back? Serve `frontend-legacy` exactly as before.

### API base configuration

By default the app assumes `https://geoleads.land/api`. To point at a different backend during development, create a `.env` file in this directory and set `VITE_DEFAULT_API_BASE`:

```
VITE_DEFAULT_API_BASE=http://localhost:8000/api
```

Restart `npm run dev` so Vite picks up the change, or just paste the URL in the UI field.

### Animate background

The landing shell now renders an animated dot grid powered by GSAP. `npm install` already pulls the dependency, but if you prune packages keep `gsap` so the effect keeps running.
