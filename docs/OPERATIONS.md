# ACTAP Operations Runbook

> **Audience**: DevOps / SRE engineers responsible for deploying and operating the ACTAP platform.

## 1. Architecture overview

```
                ┌─────────────────┐
                │   Browser       │
                │ (port 3000)     │
                └────────┬────────┘
                         │ HTTPS
                         ▼
                ┌─────────────────┐
                │  Nginx (FE)     │
                │  - static SPA   │
                │  - /api proxy   │
                └────────┬────────┘
                         │ :8001
                         ▼
                ┌─────────────────┐
                │  FastAPI (BE)   │
                │  - 4 uvicorn w. │
                │  - 5 middleware │
                └────────┬────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
        SQLite DB    API Cache    External APIs
        (volume)     (volume)     (Comtrade, IMF, ...)
```

## 2. Environments

| Env | Compose file | Env file | URL |
|-----|-------------|----------|-----|
| dev | `docker-compose.yml` | `.env.dev` | http://localhost:3000 |
| staging | `docker-compose.prod.yml` | `.env.staging` | https://staging.actap.example.com |
| prod | `docker-compose.prod.yml` | `.env.prod` | https://actap.example.com |

## 3. First-time deployment

### 3.1 Prepare the host

```bash
# Required: Docker 24+, docker-compose v2
# Required: 2 GB RAM, 20 GB disk
# Required: ports 3000 (frontend) + 8001 (backend) reachable

sudo mkdir -p /var/lib/actap/data
sudo mkdir -p /var/backups/actap
sudo useradd -r -s /usr/sbin/nologin actap
sudo chown -R actap:actap /var/lib/actap /var/backups/actap
```

### 3.2 Configure secrets

```bash
# Generate strong API key
openssl rand -hex 32

# Edit .env.prod
cp .env.prod.example .env.prod
$EDITOR .env.prod
chmod 600 .env.prod
```

### 3.3 Pull + start

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml ps
```

### 3.4 Verify

```bash
# Liveness
curl -fsS http://localhost:8001/api/health

# Readiness (DB + cache)
curl -fsS http://localhost:8001/api/health/ready | jq

# Metrics (Prometheus)
curl -fsS http://localhost:8001/api/metrics | head -20
```

## 4. Releases

### 4.1 Standard release

```bash
./deploy/scripts/release.sh v1.2.3
```

The script will:
1. Back up the SQLite database
2. Pull `actap-backend:v1.2.3`
3. Restart containers gracefully
4. Wait up to 60 s for `/api/health/ready` to return 200
5. **Auto-rollback** to the previous version if the health check fails

### 4.2 Manual release

```bash
# Pull new images
export APP_VERSION=v1.2.3
docker compose -f docker-compose.prod.yml --env-file .env.prod pull

# Recreate (zero-downtime for stateless services)
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps backend
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps frontend

# Verify
curl -fsS http://localhost:8001/api/health/ready
```

### 4.3 Rollback

```bash
# Find the previous version
docker inspect actap-backend-prod --format='{{range .Config.Env}}{{println .}}{{end}}' | grep APP_VERSION

# Roll back
export APP_VERSION=v1.2.2   # previous
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps backend frontend
```

## 5. Secret management

Production secrets are sourced from `EnvironmentFile=/etc/actap/backend.env`
in the systemd unit. **Never** commit secrets to git.

For cloud deployments, replace the systemd unit with a cloud-native mechanism:
- **AWS**: ECS task definition references SSM Parameter Store or Secrets Manager
- **GCP**: Cloud Run service references Secret Manager
- **K8s**: External Secrets Operator + Vault, or Sealed Secrets

The application code reads secrets from environment variables — the orchestration
layer is responsible for providing them.

## 6. Backups

```bash
# Daily DB backup (add to crontab)
0 3 * * * cp /var/lib/actap/data/actap.db /var/backups/actap/$(date +\%Y\%m\%d).db

# Retention: 30 days
find /var/backups/actap -name "*.db" -mtime +30 -delete
```

## 7. Monitoring

### Metrics scraping

Prometheus should scrape `/api/metrics` every 15 s.

```yaml
# prometheus.yml
scrape_configs:
  - job_name: actap
    metrics_path: /api/metrics
    static_configs:
      - targets: ['actap-backend:8001']
```

Key alerts:
- `up == 0` for 2 minutes → PagerDuty
- `actap_http_errors_total` rate > 5% → Slack
- `actap_uptime_seconds` resets → deploy notification

### Log aggregation

Production uses JSON logs to stderr. Collect with Fluent Bit / Promtail / Vector.

Required log fields: `request_id`, `level`, `event`, `path`, `status_code`, `duration_ms`.

## 8. Troubleshooting

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| `/api/health/ready` returns 503 | DB unreachable | Check `actap.db` file perms; `sqlite3 actap.db ".tables"` |
| 401 on `/api/datasources/refresh` | Missing API key | Check `X-API-Key` header against `API_KEY` in env |
| 429 on all endpoints | Rate limit hit | Wait 60 s or raise `RATE_LIMIT_PER_MINUTE` |
| Container won't start | Config validation failure | `docker logs actap-backend-prod` — see startup errors |
| Slow `/api/metrics` | High cardinality `path` labels | Aggregate rare paths to `/api/other` |

## 9. Disaster recovery

- **DB loss**: Restore from `/var/backups/actap/<date>.db` → restart backend
- **Image registry outage**: Re-tag from local image cache (`docker image ls`)
- **Host loss**: Redeploy from `.env.prod` + latest image tag via release script
- **Data corruption**: Use `release.sh` to roll back; the script preserves DB

## 10. Contacts

- On-call: <oncall@your-org.com>
- Repo: <https://github.com/your-org/actap>
- Wiki: <https://wiki.your-org.com/actap>
