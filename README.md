# Prom-Garmin-Scraper -> New name will come later.

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

## Existing Endpoints

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


# Future State

The current version of the application functions, but provides minimal value to me. It has been a good example to showcase my skillsets, but active development became increasingly difficult without a roadmap or end goal. V2 aims to become a valuable system to help me train.

The app should remain usable during development and be treated as a live product. A complete rewrite would be difficult to test and roll out, so changes should be incremental. The only user is me, but the project should still follow a deliberate SDLC process.

## Compatibility Planning

Use this section to decide what existing behavior must be preserved while the implementation evolves. It is a planning worksheet, not a promise that every current behavior is desirable.

### How to work through each endpoint

1. Record what the code does today. Mark anything not yet checked as **To verify**.
2. Record whether the route or its observable behavior has a real consumer.
3. Choose a disposition. If choosing **Replace**, say whether that means replacing the implementation while preserving the route, or introducing a new API contract.
4. State what must remain compatible, and what is allowed to change.
5. Add tests only for behavior intentionally kept or needed to safely migrate/retire a consumer. Mock provider calls; do not make contract tests depend on live services.
6. For a deprecated or replaced route, define when its old behavior can be removed.

### Disposition meanings

- **Keep** — preserve the route and its agreed observable contract. The internal implementation may change.
- **Replace** — provide a successor. Decide whether the existing route remains as a compatibility adapter during migration.
- **Deprecate** — keep the existing behavior during a transition period; remove it only after identifying consumers and a retirement condition.

### Endpoint decisions

#### `GET /metrics`

- **Disposition:** Keep.
- **Reason / direction:** Both versions may contribute metrics. Adding labels to distinguish versions may be acceptable because the Grafana dashboard and Prometheus alerts are relatively simple.
- **Current contract notes:** No request parameters. Metric names, types, and labels are defined in `app/garmin/metrics.py`. Prometheus client provides the exposition endpoint; no authentication is required.
- **To verify / decide:** Confirm the actual content type and format. Determine whether adding labels would break existing dashboard queries or alerts. Do not promise a specific error status unless it is an intentional requirement.
- **Tests / evidence:** Protect metric names, types, and labels that consumers rely on; cover dashboard/alert query compatibility where needed.
- **Removal / migration condition:** Not applicable while this endpoint is kept.

#### `GET /garmin/daily`

- **Disposition:** Keep; current version is not expected to require an API change.
- **Current contract notes:** No request parameters. Returns Garmin's daily-summary JSON, augmented with `lastUploadSyncTime`. The route also updates Prometheus metrics and checks whether the configured watch sync is stale.
- **Known edge cases:** A daily summary may not exist yet if the endpoint is called before the watch syncs. Garmin/provider failures can also occur; the current route has little explicit error handling.
- **To verify / decide:** Decide the intended response for “not synced yet” and for provider failure. Confirm whether any caller relies on the JSON response, beyond Prometheus being updated.
- **Tests / evidence:** Cover the agreed successful response and the chosen no-summary behavior. Add provider-failure coverage only to the extent needed to establish the intended endpoint behavior; mock Garmin and Slack interactions.
- **Removal / migration condition:** Not applicable while this endpoint is kept.

#### `GET /garmin/backfill`

- **Disposition:** Deprecate.
- **Reason / direction:** The current implementation was not thoroughly tested. Replace it with a more reliable data-ingestion method.
- **Current contract notes:** **To verify** the exact request, response, side effects, and whether anything calls this route.
- **To decide:** Identify any consumer and the successor workflow. Decide whether this route needs a transition period or can be retired once the successor exists.
- **Tests / evidence:** Avoid expanding tests for behavior you intend to remove; add migration or retirement checks if a consumer exists.
- **Removal condition:** Specify after identifying whether there are consumers and what replaces the route.

#### `GET /intervals/activity?id=...`

- **Disposition:** Replace.
- **Reason / direction:** The current implementation performs local file manipulation; optimize or replace that approach if the functionality is still needed.
- **Current contract notes:** Requires an activity ID and returns parsed metrics for one activity. **To verify** exact response details and side effects.
- **To decide:** Is the API itself being replaced, or only its implementation? Is this functionality used outside manual debugging?
- **Tests / evidence:** Test the contract only if it has a consumer or a planned successor; keep provider access mocked.
- **Removal condition:** Specify whether the route remains as a compatibility adapter and when it can be removed.

#### `GET /intervals/activities?weeks=...`

- **Disposition:** Deprecate.
- **Reason / direction:** Its value is unclear; similar functionality could be added in a later phase if needed.
- **Current contract notes:** `weeks` defaults to 6. Returns parsed activity metrics; walking activities are skipped. **To verify** response guarantees and consumers.
- **To decide:** Confirm whether anything uses this endpoint and whether it needs a successor.
- **Tests / evidence:** No need to preserve incidental behavior if there are no consumers and the route is retired; verify consumers before removal.
- **Removal condition:** Decide after consumer and successor checks.

#### `GET /fatigue/summary` and `POST /fatigue/summary`

- **Disposition:** Replace. `GET` is the primary compatibility contract; `POST` appears to be accidental and does not define a separate request-body contract.
- **Current contract notes:** `GET` accepts optional `weeks` (default 6) and returns a plain-text summary. It fetches recent activity history from Intervals.icu.
- **To decide:** Is the API being replaced, or only the implementation? Confirm whether anything calls `POST`; decide whether to retain it temporarily or remove it with the successor.
- **Tests / evidence:** Protect the `GET` behavior only if it has a consumer or is intentionally retained. Test POST only if a compatibility need is found.
- **Removal condition:** Define the successor and any transition needed for existing callers.

#### `POST /fatigue/diag`

- **Disposition:** Deprecate.
- **Reason / direction:** Primarily used to inspect fatigue calculations while developing. Better testing methods should be used; analysis of a particular recording may still be useful as a development tool.
- **Current contract notes:** Accepts JSON inputs for rides, a sample ride, or a requested history window; can also load an activity by ID. Returns fatigue analysis JSON.
- **To decide:** Is this only a development aid, or does it provide a useful manual diagnostic capability? If retired, what replaces that workflow?
- **Tests / evidence:** Keep calculation tests separate from this route. Add route tests only if the endpoint is intentionally retained or has a consumer.
- **Removal condition:** Decide after choosing whether the manual diagnostic workflow is still needed.
