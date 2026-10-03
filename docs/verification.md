# Verification — 2 October 2026

## Deployment preparation — 3 October 2026

The source was compared with the saved project archive before changes. Added
the production Compose overlay, Caddyfile and deployment guide. The five
frontend tests and production build passed again. The YAML service/volume
structure, secure-cookie override and port exposure were checked locally.
Docker is unavailable in this workspace, so no image build, Compose startup,
TLS certificate or live-server check was executed. Backend code was unchanged
and its test suite was not rerun in this preparation session. A Vite chunk-size
warning remains; it did not prevent the build. GitHub push and public deployment
remain pending the repository and server access.

## Original application verification

Executed on Windows with Python 3.12 and Node.js. This is a test report, not a claim of deployment or field accuracy.

## Passed

- **8 backend tests:** authentication, role restrictions, disabled accounts, origin checks, login throttling, version conflicts, assignment scope, PDF/JSON/CSV output, CSV formula escaping, timestamp validation, upload extension/size validation, neutral zone transitions and visible worker failures.
- **Real media integration:** an OpenCV-generated AVI was uploaded through the API, normalized with FFmpeg, served with HTTP Range (206), attached to a human-created incident and cut into an actual MP4 evidence clip with a JPEG thumbnail.
- **5 frontend tests:** incident links/status/timestamps, empty queue, pagination bounds, event/±10-second seeking and API error formatting.
- **Production frontend build:** Vite built the application successfully.
- **Live MongoDB integration:** API and separate worker ran against an isolated real MongoDB 8.0.6 database, not a mock, for the detector and browser checks below.
- **Real YOLO/ByteTrack smoke check:** YOLO11n loaded its actual weights and analyzed a short clip repeating the public Ultralytics example image. Four distinct video-local track IDs generated four neutral zone-entry observations. Annotated MP4 range playback succeeded. No incident was automatically created.
- **Headless Microsoft Edge journey:** sign in → create store/camera → upload a generated video → process without tracking → manually create a case → save Not an incident → play the actual evidence clip → filter the case queue. No JavaScript page errors occurred.
- **Responsive check:** 390px-wide viewport had no horizontal overflow. Desktop and mobile screenshots are included.
- **Dependency checks:** `pip check` passed; the frontend npm audit reported zero known vulnerabilities at the time of checking. This is not a comprehensive security audit.

## Important boundaries

The standard backend suite uses mongomock for isolation, while the separate live checks used MongoDB. The detector smoke image is a public example, not a retail dataset. Repeating a still image validates that inference/tracking/event/output wiring works; it does not validate person-tracking quality across retail scenes or occlusions. No model accuracy, theft-detection performance or production readiness is claimed.

Docker Desktop is not installed on the test machine. Dockerfiles and Compose configuration are supplied, but an actual Docker image build/Compose startup was **not** executed here. The application components were run directly with local processes instead. No cloud deployment, public URL, hardware CCTV connection or GitHub push was performed.

Screenshots and generated test records are synthetic workflow examples. Test credentials, database files, model weights and downloaded third-party media are excluded from the deliverable.
