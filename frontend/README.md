# Frontend Dashboard

Static browser dashboard for the Animal Detection & Re-Identification System.

## Features

- JWT login against the FastAPI backend
- Dashboard statistics and Chart.js analytics
- Live camera feed controls
- Animal profile view
- Detection history filters
- Image upload and annotated-result preview
- CSV/PDF report links
- Detection confidence settings
- Responsive Bootstrap-based layout

## Run locally

From the repository root:

```powershell
python -m http.server 5500 --directory frontend
```

Then open `http://127.0.0.1:5500`.

The dashboard defaults to `http://127.0.0.1:8000`. To use another backend URL, define this before loading the application scripts in `index.html`:

```html
<script>
  window.ANIMAL_API_BASE_URL = "http://127.0.0.1:8000";
</script>
```

Start the backend separately from `backend/` with `uvicorn app:app --reload`.

## Scope

The frontend is a thin client for the existing API. It does not perform YOLO inference or biometric matching in the browser; those operations remain in the Python backend.
