# GitHub and HTTPS deployment

These files prepare a deployment; they do not represent a completed GitHub push
or a live service.

## 1. Create the GitHub repository

In the GitHub account `muthyalamaheshkumar8-debug`, create a repository named
`retail-loss-prevention`. Leave README, license and .gitignore initialization
unchecked so the repository is empty. Choose its visibility deliberately.

If the extracted project does not already have Git initialized, run:

```sh
git init -b main
git add .
git commit -m "Prepare retail review application and HTTPS deployment"
git remote add origin https://github.com/muthyalamaheshkumar8-debug/retail-loss-prevention.git
```

Review `git status` and `git ls-files`, then push:

```sh
git push -u origin main
```

GitHub authentication must be configured on the computer running that command.
Do not commit `.env`, footage, database files or model weights.

## 2. Prepare the server

Use a Linux server with Docker Engine and the Docker Compose plugin, Git and
Python 3. The host must support long-running containers and persistent Docker
volumes. The worker, API and MongoDB run together on this one host and share
media volumes; a static web host cannot run this stack.

Choose a public domain or subdomain and point its DNS A record at the server's
public IPv4 address. Only add an AAAA record if the server has working public
IPv6. Permit inbound TCP 80 and 443, plus SSH from your administration address.
The API and MongoDB have no published ports; the frontend's 8080 binding is
restricted to server loopback.

## 3. Configure and start

On the server:

```sh
git clone https://github.com/muthyalamaheshkumar8-debug/retail-loss-prevention.git
cd retail-loss-prevention
python3 scripts/configure.py
chmod 600 .env
```

The configuration prompt creates the initial administrator credentials and a
random JWT secret. Edit `.env` to add the following, using your actual hostname
(no scheme, port or trailing slash):

```dotenv
DEPLOY_DOMAIN=review.your-domain.com
```

The production overlay sets secure cookies and the HTTPS application origin
for the API and worker. Keep `MONGODB_URI=mongodb://mongodb:27017`.

```sh
docker compose -f docker-compose.yml -f compose.production.yml config --quiet
docker compose -f docker-compose.yml -f compose.production.yml up --build -d
docker compose -f docker-compose.yml -f compose.production.yml ps
docker compose -f docker-compose.yml -f compose.production.yml logs --tail=100 backend worker caddy
```

Caddy obtains and renews the HTTPS certificate when DNS and external access to
ports 80/443 are working. Certificates are retained in `caddy-data`.
The first build and model download can take time; the server needs outbound
access to container registries, Python/npm package sources and model downloads.

## 4. Verify before sharing

Replace the example hostname below:

```sh
curl --fail https://review.your-domain.com/api/health
```

Open `https://review.your-domain.com`, sign in with your configured credentials,
then upload staged video, process it, create a case, play its evidence clip and
record a review decision. This verifies the worker and shared media, which the
API health endpoint alone does not verify. Confirm cookies are marked Secure
in the browser. Create individual accounts using the Admin page.

## Updates and data

For an update, pull the intended commit and rerun the same production `up`
command. Retain the previous commit SHA so it can be checked out and rebuilt
if an application update must be reverted.

MongoDB, uploaded media, model files and Caddy certificates use named volumes.
Keep the same checkout location/Compose project name to reuse them. Do not run
`docker compose down -v`: that deletes the stored volumes. Arrange coordinated
MongoDB/media backups and a restore check before storing valuable footage.

## References and verification limits

- [Docker Compose merge rules](https://docs.docker.com/reference/compose-file/merge/)
- [Caddy automatic HTTPS requirements](https://caddyserver.com/docs/automatic-https)

Docker is unavailable in the preparation workspace, so image builds, container
startup and TLS issuance must be verified on the deployment server. No live URL
has been created by preparing this configuration.
