# Render deployment

The root `render.yaml` Blueprint deploys the complete application:

- One Docker web service: React/Nginx, FastAPI and exactly one Python worker.
- One authenticated private MongoDB service.
- Persistent media/model storage at `/data`, plus MongoDB storage at `/data/db`.

The API and worker share the same disk inside the web service. Do not split them
into separate Render services: Render disks cannot be shared between services.
Nginx preserves same-origin `/api` requests, cookie login, large video uploads
and authenticated playback.

## Cost and sizing

This Blueprint creates **paid resources**: the web service uses `1c-2g`, MongoDB
uses `0.5c-512mb`, and their disks total 15 GB. Review Render's current quote
before deploying. These starting sizes are not load-tested capacity guarantees.
MongoDB's cache is capped at 0.25 GB; monitor memory and increase its plan if
necessary. Video conversion and tracking may need a larger web-service plan.

## Deploy

1. Sign in to Render and select **New → Blueprint**.
2. Connect `muthyalamaheshkumar8-debug/retail-loss-prevention`, branch `main`,
   using the root `render.yaml`.
3. Review the service plans, Singapore region, disk sizes and total price.
4. Enter your administrator email and a strong administrator password of at
   least 12 characters in Render's secret fields. Keep passwords out of GitHub.
   Render generates the JWT and MongoDB secrets and connects the services.
5. Approve the cost and start deployment. Wait for MongoDB and the web service
   to become healthy, then open the web service's assigned HTTPS URL.

Render's `RENDER_EXTERNAL_URL` sets the application origin; secure cookies are
always enabled. For a custom domain, set `APP_ORIGIN` to its HTTPS origin and
redeploy. Render terminates HTTPS. The project's separate Caddy configuration
is used only for the Docker-server alternative.

## Verify and maintain

Check `/api/health`, sign in, upload short staged footage, process it, manually
create a case and play the generated evidence. The health endpoint verifies
the database/API; the processing test verifies the worker and shared files.
The first tracking job downloads model weights to the persistent media disk.
Review service logs if any job fails.

Docker builds and a live Render deployment have not yet been run from this
workspace. Configuration checks do not prove the containers will start.
Both disk-backed services run one instance. Redeploys have downtime and
interrupt active processing; interrupted jobs can be reprocessed from the UI.
Use MongoDB-native backups such as `mongodump`, plus coordinated media backups.
Render advises against disk-snapshot restores for custom databases.

## Vercel

This release sends `/api` requests on the browser's own origin and uses
authenticated cookies and large uploads. Deploying only `frontend/` to Vercel
does not provide the API, database or processing worker. A separate Vercel
frontend needs additional routing and upload validation; this prepared setup
serves the complete app from Render.

## References

- https://render.com/docs/blueprint-spec
- https://render.com/docs/disks
- https://render.com/docs/docker
- https://render.com/docs/deploy-mongodb
