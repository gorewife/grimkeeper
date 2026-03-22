# Production Deployment

Deployment options for Grimkeeper. Covers systemd, Docker, and CI/CD.

PostgreSQL database required for all persistent state (timers, sessions, games).

## Persistence Requirements
- PostgreSQL database (all bot state)
- `.env` file (Discord token, database credentials)
- `discord.log` (optional, for debugging)

## Deployment Options

1. Systemd on Linux (simple, single node)
2. Docker/docker-compose (portable)
3. Kubernetes (production scale, not covered in detail)

---

## Systemd Deployment

1) Install dependencies:

```fish
# Install runtime deps
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git logrotate postgresql

# Install Pillow dependencies (for storyteller stat cards)
sudo apt install -y libjpeg-dev zlib1g-dev
```

2) Setup project:

```fish
cd ~
git clone https://github.com/gorewife/grimkeeper.git botc
cd botc
python3 -m venv .venv
source .venv/bin/activate.fish
pip install --upgrade pip
pip install -r requirements.txt
```

3) Configure environment:

```fish
# create .env with secure permissions
printf 'DISCORD_TOKEN=%s\n' "<YOUR_TOKEN>" > .env
printf 'DATABASE_URL=%s\n' "postgresql://grimkeeper_user:password@localhost:5432/grimkeeper" >> .env
chmod 600 .env
```

See `docs/DATABASE_SETUP.md` for PostgreSQL setup instructions.

Alternatively, put environment variables in `/etc/default/grimkeeper` (used by systemd unit below).

4) Example `systemd` unit (`/etc/systemd/system/grimkeeper.service`):

```ini
[Unit]
Description=Grimkeeper (botc)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/botc
EnvironmentFile=/home/ubuntu/botc/.env
ExecStart=/home/ubuntu/botc/.venv/bin/python /home/ubuntu/botc/main.py
Restart=always
RestartSec=5
StartLimitBurst=5
StartLimitIntervalSec=60

[Install]
WantedBy=multi-user.target
```

Reload systemd, enable and start:

```fish
sudo systemctl daemon-reload
sudo systemctl enable grimkeeper
sudo systemctl start grimkeeper
sudo journalctl -u grimkeeper -f
```

Notes:
- Ensure `WorkingDirectory` matches where you cloned the repo.
- Use `EnvironmentFile` to keep secrets out of the unit file. `EnvironmentFile` expects `KEY=VALUE` lines.

Log rotation: place a `logrotate` snippet (e.g., `/etc/logrotate.d/grimkeeper`) to rotate `discord.log` and old archives.

---

## Option B — Docker & docker-compose

Containerizing the bot simplifies environment consistency and deployment.

1) Example `Dockerfile` (minimal):

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
# Keep runtime state in /data
VOLUME /data
ENV DATA_DIR=/data
CMD ["python", "main.py"]
```

2) Example `docker-compose.yml`:

```yaml
version: '3.8'
services:
  botc:
    build: .
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./discord.log:/app/discord.log
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
```

Important:
- Set `DATABASE_URL` in your `.env` to point to your PostgreSQL instance (can be external or another container)
- For a local database container, add a `postgres` service to docker-compose.yml
- Example with PostgreSQL container:

```yaml
version: '3.8'
services:
  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: grimkeeper
      POSTGRES_USER: grimkeeper_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  botc:
    build: .
    restart: unless-stopped
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://grimkeeper_user:secure_password@db:5432/grimkeeper
      DISCORD_TOKEN: your_token_here
    volumes:
      - ./discord.log:/app/discord.log
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

volumes:
  pgdata:
```

Run locally:

```fish
docker compose up -d --build
docker compose logs -f
```

---

## Option C — GitHub Actions + deploy to host or registry

You can build a Docker image and push to a registry (Docker Hub, GHCR) or use Actions to SSH+rsync to your host and restart the systemd service. Keep secrets in GitHub repository secrets.

Example (deploy via SSH + rsync):

- Add these repo secrets:
  - `SSH_USER` (e.g., `ubuntu`)
  - `SSH_HOST` (hostname/IP)
  - `SSH_KEY` (private key contents)
  - `DISCORD_TOKEN` (bot token)
  - `DATABASE_URL` (PostgreSQL connection string)

Minimal workflow steps:
1. Checkout code
2. Run tests
3. Upload code to host via `rsync` over SSH
4. SSH into host, ensure PostgreSQL is configured
5. Run `pip install -r requirements.txt`
6. Run `sudo systemctl restart grimkeeper`

When using Actions to push Docker images, set `DISCORD_TOKEN` and other secrets in GitHub Secrets and inject them into the container runtime via your host's deployment system (do not bake secrets into images).

Deploy template note
--------------------
The repository includes a `deploy/docker-compose.yml` template. The deploy workflow will attempt to upload this template to the host before performing the remote deploy. If the file is present on the host the workflow will prefer `docker compose pull && docker compose up -d`; otherwise it falls back to `docker run`. If you manage the compose file on the host manually, the upload step is harmless and will not overwrite existing files unless permissions allow.

---

## Secrets & token management

- DO NOT commit `.env` to the repo. Ensure it's in `.gitignore`.
- For CI and deployment automation, use your platform's secrets manager (GitHub Secrets, AWS Secrets Manager, GitLab CI variables, etc.).
- Store both `DISCORD_TOKEN` and `DATABASE_URL` securely
- If a token is ever exposed, revoke/rotate it immediately via the Discord Developer Portal.
- For database credentials, rotate passwords periodically and use strong passwords

Recommended pattern for automated deploys (GitHub Actions):
- Store `DISCORD_TOKEN` and `DATABASE_URL` as repo secrets and pass them as environment variables only at runtime (e.g., via SSH `EnvironmentFile` or container runtime environment variables).

---

## Backups & persistence

- Backup PostgreSQL database regularly (e.g., nightly). Sample backup command:

```fish
# Using pg_dump
pg_dump $DATABASE_URL > ~/botc-backup-$(date +%Y%m%d).sql

# Or with compression
pg_dump $DATABASE_URL | gzip > ~/botc-backup-$(date +%Y%m%d).sql.gz
```

- For Docker/RDS, use automated backup features
- Store backups in remote storage (S3, GCS, Backblaze) for durability
- Test your restore process periodically

Restore process:
1. Stop the bot service/container
2. Restore database: `psql $DATABASE_URL < backup.sql`
3. Start the bot service/container

**AWS RDS Automated Backups:**
- RDS provides automated daily backups with point-in-time recovery
- Configure backup retention period (7-35 days recommended)
- Enable automated backups in RDS console

**Docker Volume Backups:**
- If using docker-compose with PostgreSQL container, backup the named volume:
```fish
docker run --rm -v botc_pgdata:/data -v (pwd):/backup ubuntu tar czf /backup/pgdata-backup-(date +%Y%m%d).tar.gz /data
```

---

## Health checks, monitoring & logs

- systemd: use `systemctl status` and `journalctl -u grimkeeper`.
- Docker: use `docker compose logs -f` and health checks if you add them to the container image.
- PostgreSQL: monitor connection count, query performance, and disk usage
- Use a process monitor (Prometheus + node exporter, or simple uptime alerts) to restart or alert on repeated crashes.
- Log rotation: rotate `discord.log` and set limits on Docker log size.
- Database monitoring: Check active connections with `SELECT count(*) FROM pg_stat_activity WHERE datname = 'grimkeeper';`

Example basic health check for containers (docker-compose): add a `healthcheck` to `docker-compose.yml` that tests database connectivity. For systemd, rely on `Restart=always` and external monitoring to raise alerts.

---

## Operational tips

- Run the bot as a dedicated user (e.g., `ubuntu` on AWS) and ensure file permissions are restricted.
- Keep dependencies updated, but test upgrades in a staging environment before applying to production.
- Monitor disk usage for logs and PostgreSQL database.
- Ensure PostgreSQL has sufficient resources (RAM, connections, disk I/O).
- Consider a read-only maintenance mode (stop service) before performing database restores.

## Example quick commands (fish shell)

Activate local venv and run (dev):

```fish
python3 -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt
set -x DISCORD_TOKEN "<YOUR_TOKEN>"
python3 main.py
```

Run tests locally:

```fish
pip install pytest
pytest -q
```

---

## Advanced: Kubernetes / managed deployments

If you deploy at scale, run the bot in Kubernetes with:
- External PostgreSQL (managed database like RDS, Cloud SQL, etc.)
- Secrets object for `DISCORD_TOKEN` and `DATABASE_URL`
- Liveness/readiness probes for health checks
- Horizontal pod autoscaling based on metrics

For HA: The bot can run multiple replicas since all state is in PostgreSQL. Use a shared database connection and ensure your connection pool size accounts for multiple instances.

---

## Quick checklist before going live

- [ ] Ensure `DISCORD_TOKEN` and `DATABASE_URL` are set in environment or `EnvironmentFile` and never committed
- [ ] PostgreSQL database is properly configured with backups enabled
- [ ] Database connection pooling is configured (default: min=2, max=10)
- [ ] Configure log rotation and retention
- [ ] Configure a process restart policy (systemd Restart or Docker restart)
- [ ] Add Alerts/monitoring for repeated restarts or high error rates
- [ ] Test a database restore from backup in a staging environment
- [ ] Verify all 5 migrations ran successfully (check `discord.log` on startup)

---

If you want, I can also:
- Add a sample `grimkeeper.service` unit file into the repo's `deploy/` directory
- Add a `Dockerfile` and `docker-compose.yml` into `deploy/` along with an example GitHub Actions workflow that pushes a Docker image to GHCR and deploys via SSH
- Provide a sample `logrotate` config and backup script

These additions make automated deployments repeatable and easy to review in PRs.
