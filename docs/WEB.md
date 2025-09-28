Web build and PWA notes
=======================

Prereqs
- Python 3.11 recommended
- Install pygbag: `pip install pygbag`

Build (local)
- From repo root: `python3 -m pygbag --build .`
- Output goes to: `build/web/`

Serve locally
- `python3 -m http.server -d build/web 8000`
- Open: `http://localhost:8000/web/` or `http://localhost:8000/` depending on pygbag output

Notes
- Browser storage is used for profiles, settings, scores (localStorage)
- First user interaction is required before audio can play

Deploy
- Upload `build/web/` to any static host (GitHub Pages, Netlify, Vercel static)
- Ensure `index.html`, `manifest.webmanifest`, `service-worker.js`, wasm/runtime files, and `assets/**` are all reachable with the same relative paths as in local build

