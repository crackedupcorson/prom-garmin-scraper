vi# prom-garmin-scraper

This repository contains the v2 implementation of a personal training-intelligence service. It currently combines Garmin wellness data, Intervals.icu activity data, Prometheus metrics, and Helm deployment configuration.

The intended destination is a durable, explainable service that can answer, with evidence and uncertainty:

- What training was completed?
- Is the usual easy session becoming easier to repeat?
- Is current workload being tolerated?
- Are recovery mismatches persistent across comparable sessions?
- What data is missing or too incomparable to interpret?

It is not a workout prescription engine, medical assessment, or composite readiness-score system.

## Source of truth

Product requirements and implementation guidance live in:

- [.github/agents/TRAINING_INTELLIGENCE_RECOMMENDATIONS.md](.github/agents/TRAINING_INTELLIGENCE_RECOMMENDATIONS.md)
- [.github/agents/FEATURE_IMPLEMENTATION.md](.github/agents/FEATURE_IMPLEMENTATION.md)
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), the phased repository backlog derived from those documents

The agent documents supersede older project descriptions.

## Current implementation

The repository is a prototype with these foundations:

- Flask application and `/metrics` Prometheus exposition.
- Garmin/Garth authentication and daily wellness retrieval.
- Intervals.icu activity metadata and stream parsing.
- Rule-based fatigue primitives in `app/garmin/fatigue.py`.
- Helm Deployment, Service, PVC, and PrometheusRule templates.
- Unit tests and fixture data for the existing fatigue behavior.

The canonical database, migration-backed storage, incremental sync orchestration, resumable backfill, scheduled jobs, health endpoints, and durability analytics are planned work. See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## Local development

The application targets Python 3.11+, with dependencies listed in [requirements.txt](requirements.txt). Runtime credentials and provider configuration must be supplied through the configured environment or Kubernetes Secrets; do not commit them.

The test suite should be run from the project environment with:

```bash
pytest -q
```

Provider-dependent tests should use mocks or fixtures and must not require live Garmin, Intervals.icu, Slack, Prometheus, or Kubernetes services.

## Local container build and run

The application is packaged as a Docker container and listens on port `8080` when started by the entrypoint in `app/python-scraper.py`.

Build the image from the repository root:

```bash
docker build -t prom-garmin-scraper .
```

Run it locally with your environment variables loaded from a local `.env` file or via `-e` flags:

```bash
cat > .env <<'EOF'
GARMIN_USER=your-garmin-user
GARMIN_PASS=your-garmin-password
GARTH_FOLDER=/tmp/garth
INTERVALS_API_KEY=your-intervals-key
SLACK_BOT_TOKEN=your-slack-token
SLACK_CHANNEL=your-slack-channel
SLACK_USER_ID=your-slack-user-id
EOF

docker run --rm -it \
  --env-file .env \
  -p 8080:8080 \
  prom-garmin-scraper
```

Once the container is running, the service is available at:

- `http://localhost:8080/metrics`
- `http://localhost:8080/garmin/daily`

> The Dockerfile uses the official multi-architecture Python image. A regular `docker build` creates an image for your host architecture; the GitHub Actions workflow publishes both `linux/amd64` and `linux/arm64` variants for K3s to select automatically. To build an ARM64 image locally from another architecture, use `docker buildx build --platform linux/arm64 --load -t prom-garmin-scraper .`.

## Existing endpoints

These routes are compatibility interfaces while the v2 services are introduced:

- `GET /metrics` — Prometheus metrics.
- `GET /garmin/daily` — Current Garmin retrieval and metric population.
- `GET /garmin/backfill` — Legacy backfill interface; scheduled to be replaced by the bounded CLI workflow.
- `GET /intervals/activity?id=...` — Parse one Intervals.icu activity.
- `GET /intervals/activities?weeks=...` — Retrieve and parse recent activities.
- `POST /fatigue/diag` — Existing fatigue diagnostic interface.
- `GET /fatigue/summary` — Existing plain-text fatigue summary.

These endpoints currently perform live provider work and should not be treated as the final sync or reporting architecture.

## Deployment

The service is packaged for Kubernetes/K3s with Helm. The current chart uses a single Deployment and PVC and exposes Prometheus scrape annotations. Scheduled sync and analysis CronJobs, health probes, durable storage configuration, and safer secret handling are part of Phase 1 in the implementation plan.

Do not deploy changes automatically to the live cluster.
