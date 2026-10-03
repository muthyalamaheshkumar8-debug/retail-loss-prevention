# Free Render + MongoDB Atlas deployment

The default `render.yaml` now creates **one Free web service**. It has no paid
private service, disk, worker service or database. Leave billing details unset.
MongoDB is provided separately by an Atlas **M0 Free** cluster.

## What the free version supports

React/Nginx, FastAPI and one Python worker run together in a lightweight Docker
image. Login, store administration, short video uploads, conversion, playback,
human-created cases, evidence generation and reports remain available.

Person detection/ByteTrack is disabled (`CV_ENABLED=false`), and Torch/YOLO are
excluded from this image. Upload limits are 20 MB, two minutes and 921,600 pixels
(about 720p). FFmpeg uses one output thread. The local Docker Compose application
still supports the original person tracking and persistent volumes.

**This is a temporary demo, not durable footage storage.** Render Free spins
down after 15 minutes without inbound traffic. Uploaded videos and evidence
are lost on spin-down, restart or redeploy. Atlas keeps database records, but
those records cannot restore deleted media. The free build shows this warning
inside the application. Download evidence you need before the instance sleeps.
Small simultaneous jobs may still exhaust the free instance's resources; use
short staged footage and one processing job at a time.

## 1. Configure the free database

Create or use a MongoDB Atlas account, then deploy an **M0 Free** cluster. Do not
select Flex or a dedicated paid cluster. Choose a supported nearby region.
Create an application database user with `readWrite` permission only for the
`loss_prevention` database; keep the password private.

In Atlas Network Access, allow the outbound IP ranges shown for your Render
service in its dashboard. Do not automatically allow `0.0.0.0/0`.
In Atlas Connect, select Drivers/Python and copy the `mongodb+srv://` connection
string. Replace the user/password placeholders, URL-encoding reserved password
characters, and use the `loss_prevention` database where appropriate.

## 2. Configure Render without a card

1. Select New → Blueprint and this GitHub repository, branch `main`, path
   `render.yaml`. Use `retail-review-free` as the Blueprint name.
2. The proposal must show one Free web service and no paid disks/private
   services. If a card prompt appears, stop instead of entering billing details.
3. Enter `MONGODB_URI`, `ADMIN_EMAIL` and `ADMIN_PASSWORD` in Render's secret
   fields. Use at least 12 characters for the administrator password. Do not
   send these secrets in chat or commit them to GitHub. The Blueprint generates
   the JWT secret.
4. Create the free service. Add its Render outbound IP ranges to Atlas, if not
   already configured, then retry the deploy if the first connection fails.
5. Open the assigned HTTPS URL directly. Render's `RENDER_EXTERNAL_URL` sets
   the allowed origin and secure cookies are enabled. For a custom domain, set
   `APP_ORIGIN` explicitly to its HTTPS origin.

A Blueprint imported through a public repository URL does not gain automatic
GitHub deployments until the provider/repository is connected. Manual deploys
remain possible without granting new GitHub permissions.

## 3. Verify

Check `/api/health`, sign in, add a store/camera, upload a small staged video,
process without tracking, create a case and play/download its evidence.
The HTTP health check alone does not prove the worker processed a video.
Do not label the service live until its deploy and workflow checks succeed.

Render allows 750 free instance hours per workspace/month and has bandwidth
and build limits. With no payment method, exceeding applicable limits causes
suspension or disabled builds instead of supplementary billing. Never upgrade
instances or add paid disks for this no-payment setup.

## Other free JavaScript hosting

Cloudflare Workers has a free plan without a credit card and supports a subset
of Node.js APIs. It is an option for lightweight JavaScript/TypeScript APIs;
it cannot directly run this Python/FFmpeg worker. Converting this application
would require a separate implementation and a video-processing solution.

Hugging Face's current documentation requires a paid plan to create Docker
Spaces, despite CPU Basic hardware having no hourly cost. Koyeb's current
pricing FAQ requires card verification. Neither meets this no-payment request.

## References checked 3 October 2026

- https://render.com/docs/free
- https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/
- https://www.mongodb.com/resources/products/fundamentals/create-database
- https://www.cloudflare.com/products/workers/
- https://developers.cloudflare.com/workers/runtime-apis/nodejs/
- https://huggingface.co/docs/hub/spaces-overview
- https://www.koyeb.com/docs/faqs/pricing
