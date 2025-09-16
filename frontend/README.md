# Frontend (Static)

Minimal static UI that hits the FastAPI service for case data.

## Quick start
1. `cd frontend`
2. Serve the directory with any static server (examples below).

### Python (3.x)
```
python -m http.server 5173
# then open http://localhost:5173
```

### Node (if installed)
```
npx serve .
```

Once loaded, paste the API base URL (e.g. `http://157.230.11.23:8000`) and click **Refresh**.

## Notes
- All filtering happens client side; the page fetches up to 250 rows via `GET /cases`.
- Toggle “Show last 24 hours only” to add the `since_hours=24` query.
- Update styling or add routing as needed; this is plain HTML/CSS/JS so it can later be replaced by React or another framework.
