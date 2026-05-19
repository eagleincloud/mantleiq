# MantleIQ Workflows

Prefect-based orchestration for automated data pipelines.

## What is Prefect?

**Prefect** is a workflow orchestration platform that automates, monitors, and schedules data pipelines.

### Key Benefits for MantleIQ:

1. **Automated Scheduling** — Run data ingestion daily without manual intervention
2. **Retry Logic** — Automatically retry failed tasks (e.g., if network fails, retry 3x)
3. **Task Dependencies** — Define workflow stages: ingest → normalize → feature → score → cluster
4. **Monitoring & Alerts** — Real-time dashboards, Slack notifications on failure
5. **Data Lineage** — Track: "This zone comes from these data sources ingested on this date"
6. **Error Handling** — Detailed logs for debugging pipeline failures

### Use Case in MantleIQ:

Instead of manually running scripts like:
```bash
python scripts/ingest_faults.py faults.zip basin123
python scripts/ingest_heatflow.py heatflow.csv basin123
python scripts/batch_feature_compute.py basin123
python scripts/score_zones.py basin123
```

Prefect **automatically orchestrates** all steps:

```
Cloud Scheduler (Daily 2:00 AM UTC)
    ↓
Prefect Flow: data_pipeline_flow
    ├─ Fetch vector data (USGS)
    ├─ Ingest faults → PostgreSQL
    ├─ Ingest geology → PostgreSQL
    ├─ Fetch raster data (NOAA)
    ├─ Ingest gravity/magnetic
    ├─ Fetch heat flow (IHFC)
    ├─ Ingest heat flow points
    ├─ Normalize all data
    ├─ Compute 25+ features
    ├─ Score zones (6-factor + ML)
    ├─ Cluster prospect zones
    ├─ Generate PDF reports
    └─ Slack notification: "✅ Pipeline complete!"
```

---

## Installation

```bash
pip install prefect>=3.0.0 geopandas geoalchemy2
```

## Configuration

### 1. Set Prefect API Key (Optional, for cloud)

```bash
prefect cloud login
# Or set environment variable
export PREFECT_API_URL="https://api.prefect.cloud/api/accounts/<account-id>/workspaces/<workspace-id>"
export PREFECT_API_KEY="<your-api-key>"
```

### 2. Environment Variables

Create `.env` in backend directory:

```
MANTLEIQ_DATABASE_URL=postgresql://user:pass@localhost/mantleiq
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
```

---

## Running Workflows

### Local Test Run

```bash
cd backend
python workflows/data_pipeline.py
```

### Deploy to Prefect Cloud

```bash
# Create a deployment
prefect deployment build workflows/data_pipeline.py -n mantleiq-daily

# Schedule it (daily at 2:00 AM UTC)
prefect deployment schedule set mantleiq-daily --cron "0 2 * * *"

# Start the Prefect worker (local or remote)
prefect worker start --pool default
```

### Monitor in Prefect UI

Open https://app.prefect.cloud to see:
- Pipeline execution history
- Task-level logs and timings
- Failure alerts
- Data lineage

---

## Workflow Structure

### `data_pipeline.py`

**Main flow:** `data_pipeline_flow(basin_id)`

**Tasks (in order):**

| Phase | Tasks | Input | Output |
|-------|-------|-------|--------|
| **1. Ingest** | `fetch_vector_data` → `ingest_vector_data` | USGS/Macrostrat URLs | PostgreSQL tables |
| | `fetch_raster_data` → `ingest_raster_data` | NOAA URLs | COG metadata |
| | `fetch_point_data` → `ingest_point_data` | IHFC CSV | PostgreSQL table |
| **2. Normalize** | `normalize_data` | Raw tables | Validated, EPSG:4326 |
| **3. Feature** | `compute_features` | Features table | Computed 25+ metrics |
| **4. Score** | `score_zones` | Features | Scores, ranks, confidence |
| **5. Cluster** | `cluster_zones` | Scores | Prospect zone geometries |
| **6. Export** | `generate_reports` | Zones | PDF reports |
| **7. Notify** | `send_notification` | Status | Slack/Email alert |

### Task Retries

Each task has automatic retry logic:

```python
@task(name="ingest_vector_data", retries=2, retry_delay_seconds=60)
```

If task fails → wait 60s → retry (up to 2 times).

---

## Extending the Workflow

### Add a New Task

```python
@task(name="my_task", retries=1)
def my_task(param: str):
    logger = get_run_logger()
    logger.info(f"Processing {param}")
    # Do work
    return result

# Add to flow:
data_pipeline_flow(basin_id):
    my_result = my_task("value")
```

### Add a Scheduled Trigger

```bash
prefect deployment schedule set mantleiq-daily \
  --cron "0 2 * * 1-5"  # Weekdays at 2:00 AM
```

### Add Slack Notifications

Update `send_notification`:

```python
import requests

webhook_url = os.getenv("SLACK_WEBHOOK_URL")
requests.post(webhook_url, json={
    "text": f"MantleIQ: {notification}"
})
```

---

## Troubleshooting

### Pipeline Hangs

Check Prefect logs:
```bash
prefect flow-run logs <flow-run-id>
```

### Task Fails Repeatedly

Increase retries and delay:
```python
@task(retries=5, retry_delay_seconds=300)
```

### Database Connection Issues

Verify database URL:
```bash
echo $MANTLEIQ_DATABASE_URL
sqlalchemy-utils db_url_ready $MANTLEIQ_DATABASE_URL
```

---

## Next: Phase 2 (Weeks 7-10)

Enhancements to add:

- [ ] ML model training integration (XGBoost)
- [ ] Data quality scoring (coverage, resolution, age)
- [ ] Parallel basin processing (run 10 basins concurrently)
- [ ] Custom metrics (execution time, data volume, API response time)
- [ ] Webhooks to external systems (notify client dashboards)

---

**Documentation:** https://docs.prefect.io/  
**Community:** https://discuss.prefect.io/
