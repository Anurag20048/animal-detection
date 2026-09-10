# Portfolio Demo Checklist

Use this checklist before showing the project in an interview or adding screenshots to the README.

## Backend

- [ ] Install `backend/requirements.txt`.
- [ ] Configure `.env` from `.env.example`.
- [ ] Confirm the configured YOLO model exists.
- [ ] Start FastAPI with Uvicorn.
- [ ] Open `/health` and confirm the service responds.

## Dashboard

- [ ] Start the frontend with `python -m http.server 5500 --directory frontend`.
- [ ] Log in with a locally configured account.
- [ ] Verify dashboard statistics load.
- [ ] Register one animal profile.
- [ ] Run image detection with a representative image.
- [ ] Confirm the result shows a detection, confidence, and animal ID when the full ML runtime is available.
- [ ] Check detection history and the animal profile.
- [ ] Verify CSV/PDF reporting if the configured backend supports it.

## Interview-safe claims

Say that the project demonstrates an end-to-end prototype for detection, tracking, visual embedding, similarity-based re-identification, persistence, and a web dashboard.

Do not claim production biometric accuracy, automatic geolocation, or validated buffalo detection unless you have run a documented benchmark with appropriate data and model weights.
