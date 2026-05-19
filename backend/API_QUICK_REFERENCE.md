# API Quick Reference

**Base URL:** `http://localhost:8000`  
**Docs:** `http://localhost:8000/docs`

---

## Basins

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/basins` | List all basins |
| GET | `/basins/{basin_id}` | Get basin details |
| POST | `/basins` | Create new basin |

```bash
# List basins
curl http://localhost:8000/basins

# Create basin
curl -X POST http://localhost:8000/basins \
  -H "Content-Type: application/json" \
  -d '{"name":"Kansas Rift","region":"Midwest","country":"USA"}'
```

---

## Analysis

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/analysis/run` | Start analysis job |
| GET | `/analysis/jobs/{job_id}` | Check job status |
| GET | `/analysis/jobs/{job_id}/results` | Get job results |

```bash
# Start analysis (returns job_id)
curl -X POST http://localhost:8000/analysis/run \
  -H "Content-Type: application/json" \
  -d '{"basin_id":"<uuid>","mode":"standard"}'

# Check status
curl http://localhost:8000/analysis/jobs/{job_id}
```

---

## Zones

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/zones/{zone_id}` | Get zone details |
| GET | `/zones?basin_id={id}` | List basin zones |
| POST | `/zones/compare` | Compare zones |

```bash
# Get zone detail
curl http://localhost:8000/zones/{zone_id}

# Compare zones
curl -X POST http://localhost:8000/zones/compare \
  -H "Content-Type: application/json" \
  -d '{"zone_ids":["uuid1","uuid2"]}'
```

---

## Export

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/export/report` | Generate PDF |
| GET | `/export/reports/{report_id}` | Report status |
| GET | `/export/reports/{report_id}/download` | Download PDF |
| GET | `/export/basins/{basin_id}/results?format=geojson` | Export data |

```bash
# Generate PDF
curl -X POST http://localhost:8000/export/report \
  -H "Content-Type: application/json" \
  -d '{"zone_id":"<uuid>","include_map":true}'

# Export GeoJSON
curl "http://localhost:8000/export/basins/{basin_id}/results?format=geojson"

# Export CSV
curl "http://localhost:8000/export/basins/{basin_id}/results?format=csv"
```

---

## Health

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Service status |
| GET | `/` | API info |

```bash
curl http://localhost:8000/health
```

---

## Common Responses

### Success (200/201/202)
```json
{
  "id": "uuid",
  "status": "ok|pending|completed",
  "data": {}
}
```

### Error (400/404/500)
```json
{
  "detail": "Error message",
  "error_type": "Exception type",
  "error_code": "CODE"
}
```

---

## Zone Score Breakdown

```json
{
  "prospectivity_score": 82.5,        // Overall score (0-100)
  "confidence_score": 0.85,            // Confidence (0.5-1.0)
  "score_class": "High-priority",      // Interpretation
  "components": {
    "f_generation": 0.85,              // 6 weighted factors
    "f_fluid_interaction": 0.80,
    "f_structural_pathways": 0.75,
    "f_trap_retention": 0.78,
    "f_surface_indicators": 0.90,
    "f_thermodynamic": 0.70
  },
  "top_features": [                    // Attribution
    {"name": "fault_intersection", "contribution": 27.6},
    {"name": "seep_proximity", "contribution": 17.6}
  ]
}
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async job) |
| 400 | Bad request |
| 404 | Not found |
| 500 | Server error |

---

## Job Statuses

- `queued` — waiting to run
- `running` — in progress
- `completed` — success
- `failed` — error

---

## Examples

### Full Workflow

```bash
# 1. List basins
curl http://localhost:8000/basins

# 2. Get basin detail
curl http://localhost:8000/basins/<basin_id>

# 3. Start analysis
JOB=$(curl -X POST http://localhost:8000/analysis/run \
  -H "Content-Type: application/json" \
  -d '{"basin_id":"<id>"}' | jq -r '.analysis_id')

# 4. Check progress
curl http://localhost:8000/analysis/jobs/$JOB

# 5. Get results
curl http://localhost:8000/analysis/jobs/$JOB/results

# 6. Get top zone
ZONE=$(curl http://localhost:8000/zones?basin_id=<id> | jq -r '.[0].id')

# 7. View zone detail
curl http://localhost:8000/zones/$ZONE

# 8. Export PDF
curl -X POST http://localhost:8000/export/report \
  -H "Content-Type: application/json" \
  -d "{\"zone_id\":\"$ZONE\"}"

# 9. Export GeoJSON
curl "http://localhost:8000/export/basins/<id>/results?format=geojson"
```

---

**See full API docs:** http://localhost:8000/docs
