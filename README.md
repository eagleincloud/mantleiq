# MantleIQ - Natural Hydrogen Prospectivity Engine

> AI-powered geospatial discovery system for natural hydrogen exploration

## Overview

**MantleIQ Discovery Engine** is a geospatial AI platform that scores natural hydrogen prospectivity across sedimentary basins using:

- **6-factor scoring methodology** (hydrogen generation, fluid interaction, structural pathways, trap retention, surface indicators, thermodynamic favorability)
- **Confidence-adjusted modeling** accounting for data completeness and quality
- **Hybrid rule-based + ML ensemble scoring** for robust predictions
- **Interactive map visualization** with feature attribution and explainability
- **Automated PDF export** with detailed analysis briefings

## Quick Start

### Prerequisites
- Docker & Docker Compose
- PostgreSQL 15 + PostGIS 3.4 (containerized)
- Python 3.11+
- Node.js 22+
- Git

### 1. Clone & Setup
```bash
git clone <repo-url> mantleiq-mvp
cd mantleiq-mvp

# Copy environment file
cp .env.example .env
```

### 2. Configure Supabase Connection
Edit `.env` file with your Supabase credentials:
```env
DATABASE_URL=postgresql+psycopg2://postgres:[PASSWORD]@db.ttimdqokzalxluwmezcz.supabase.co:5432/postgres
```

Then create database schema:
```bash
# See SUPABASE_SETUP.md for detailed instructions
# Copy infra/sql/001_schema.sql into Supabase SQL Editor and run
```

### 3. Start Local Development Stack
```bash
docker compose up --build
```

This starts:
- **FastAPI Backend** on `localhost:8000` (connects to Supabase)
- **React Frontend** on `localhost:5173`

Note: Database is now on Supabase (no local PostgreSQL container)

### 3. Access the Application

**Frontend:** http://localhost:5173
- Select a basin (Kansas Rift demo)
- Click "Run Analysis"
- Explore ranked zones on the map
- View feature attribution for each zone
- Export PDF briefing

**API Docs:** http://localhost:8000/docs (Swagger UI)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend (React)                      │
│   BasinSelector | MapView | RankingList | ZonePanel         │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/JSON
┌─────────────────────┴───────────────────────────────────────┐
│                    FastAPI Backend                          │
│  /basins | /results | /zones | /run-analysis | /export     │
├─────────────────────────────────────────────────────────────┤
│  Scoring Service | Feature Engine | Explainability | Export│
└─────────────────────┬───────────────────────────────────────┘
                      │ SQL/Spatial
┌─────────────────────┴───────────────────────────────────────┐
│          PostgreSQL + PostGIS + Cloud Storage              │
│  Tables: basins, grid_cells, features, zones, reports      │
│  Rasters: gravity, magnetic, DEM (Cloud Optimized GeoTIFF) │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
mantleiq-mvp/
├── config/
│   ├── datasets.yaml           # Data source registry
│   ├── model.yaml              # Scoring weights + ML params
│   └── pipeline.yaml           # Feature engineering flows
├── infra/
│   ├── sql/
│   │   └── 001_schema.sql      # PostGIS schema
│   └── terraform/              # GCP IaC (coming soon)
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app
│   │   ├── api/                # Endpoints
│   │   ├── core/               # Config, DB
│   │   ├── models/             # Scoring logic
│   │   ├── services/           # Feature, explainability, export
│   │   └── utils/              # Validators
│   ├── scripts/                # Data ingestion, batch jobs
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # MapView, ZonePanel, etc.
│   │   ├── services/           # API client
│   │   ├── hooks/              # State management
│   │   └── styles/             # CSS
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── .env.example
```

## Data Ingestion (Phase 1)

To populate the database with real geospatial data:

```bash
# Ingest USGS faults (vector)
python backend/scripts/ingest_vector.py \
  --path /path/to/faults.shp \
  --table faults \
  --source-crs EPSG:4326

# Ingest heat flow points (CSV)
python backend/scripts/ingest_point_csv.py \
  --path /path/to/heatflow.csv \
  --table heatflow_points \
  --lon-col lon \
  --lat-col lat

# Register raster metadata (gravity GeoTIFF)
python backend/scripts/ingest_raster_metadata.py \
  --path /path/to/gravity.tif
```

Data sources:
- **Macrostrat** (lithology): `https://macrostrat.org/api/v2`
- **USGS Faults**: `https://www.usgs.gov/programs/earthquake-hazards/faults`
- **NOAA Gravity**: `https://www.ncei.noaa.gov/products/gravity-data`
- **NOAA EMAG2** (magnetic): `https://www.ncei.noaa.gov/products/earth-magnetic-model-anomaly-grid-2`
- **IHFC Heat Flow**: `https://www.ihfc-iugg.org/products/global-heat-flow-database/data`
- **NASA SRTM** (DEM): `https://www.earthdata.nasa.gov/data/instruments/srtm`

## Scoring Methodology

### Formula
```
S_score = (
  0.30 × F_generation +
  0.20 × F_fluid_interaction +
  0.20 × F_structural_pathways +
  0.15 × F_trap_retention +
  0.10 × F_surface_indicators +
  0.05 × F_thermodynamic
) × C

Where:
C = 0.5 + 0.5 × confidence_raw
confidence_raw = 0.40×data_coverage + 0.40×data_quality + 0.20×missing_data_completeness
```

### Score Interpretation
| Score | Interpretation |
|-------|----------------|
| 80–100 | High-priority target |
| 65–79 | Strong prospect, needs validation |
| 50–64 | Moderate prospect |
| 35–49 | Weak / speculative |
| <35 | Low priority |

## API Endpoints

### Basin Management
- `GET /basins` — List all basins
- `GET /basins/{basin_id}` — Get basin details

### Analysis
- `POST /run-analysis` — Trigger prospectivity analysis
- `GET /job/{job_id}` — Check analysis job status
- `GET /results/{basin_id}` — Get zones + rankings

### Zone Details
- `GET /zones/{zone_id}` — Zone score, features, attribution
- `POST /export-report/{zone_id}` — Generate PDF brief
- `POST /compare` — Compare multiple zones

### Diagnostics
- `GET /health` — Service health check
- `GET /docs` — Swagger UI
- `GET /openapi.json` — OpenAPI schema

## Configuration

### Model Weights (`config/model.yaml`)
Adjust scoring factor weights:
```yaml
weights:
  f_generation: 0.30        # Hydrogen generation potential
  f_fluid_interaction: 0.20 # Fluid circulation capability
  f_structural_pathways: 0.20 # Structural permeability
  f_trap_retention: 0.15    # Trapping geometry + seal
  f_surface_indicators: 0.10 # Known seeps/anomalies
  f_thermodynamic: 0.05     # Temperature window favorability
```

### Grid Parameters (`config/model.yaml`)
```yaml
grid:
  cell_size_km: 10
  grid_type: h3
  h3_resolution: 5          # ~11 km cells
  clustering_method: dbscan
  dbscan_eps_km: 12
  dbscan_min_samples: 4
```

### Feature Engineering (`config/pipeline.yaml`)
Define which features to compute and in what order.

## Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Start API server
uvicorn app.main:app --reload --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start dev server with HMR
npm run dev

# Build for production
npm run build
```

### Database Migrations

Schema updates go in `infra/sql/`:
```bash
# Apply migration
psql -U mantleiq -d mantleiq -f infra/sql/002_migration_name.sql
```

## Testing

```bash
# Backend unit tests
pytest backend/tests/ -v

# Frontend unit tests (coming soon)
npm test

# Integration tests (local Docker stack)
pytest tests/integration/
```

## Deployment

### Local Docker
```bash
docker compose up --build
```

### GCP Cloud Run + Cloud SQL
Requires Terraform (coming in Phase 4):
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

See `infra/terraform/README.md` for GCP setup details.

## Performance Optimization

### Database
- PostGIS spatial indexes (GIST) on geometry columns
- Analyze slow queries: `EXPLAIN ANALYZE`
- CloudSQL Insights for cloud deployments

### Frontend
- Lazy load zone detail components
- MapLibre vector tile caching
- Cloud CDN for static assets

### API
- Connection pooling (SQLAlchemy)
- Query result caching (Redis, optional)
- Response compression (gzip)

## Troubleshooting

### Database Connection Error
```
psql: error: could not translate host name "db" to address
```
→ Make sure `docker compose up` has completed and containers are healthy:
```bash
docker compose ps
```

### Feature Ingestion Fails
```
geometry_column 'geometry' not found
```
→ Ensure `infra/sql/001_schema.sql` has been applied:
```bash
docker compose exec db psql -U mantleiq -d mantleiq -f /docker-entrypoint-initdb.d/001_schema.sql
```

### Map Not Loading
→ Check API endpoint in `.env`:
```env
VITE_API_URL=http://localhost:8000
```

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Commit changes: `git commit -m "Add: my feature"`
3. Push: `git push origin feature/my-feature`
4. Open a Pull Request

## Roadmap

- **Phase 0** (Weeks 1-2): Foundation (infra, schema, shell)
- **Phase 1** (Weeks 3-6): Data Backbone (ingest, features)
- **Phase 2** (Weeks 7-10): AI Engine (scoring, clustering, UI)
- **Phase 3** (Weeks 11-13): Productionization (automation, export)
- **Phase 4** (Weeks 14-16): Launch (security, monitoring, deploy)

## Documentation

- [API Reference](docs/API_REFERENCE.md)
- [Data Dictionary](docs/DATA_DICTIONARY.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Runbook](docs/RUNBOOK.md)

## License

Proprietary. MantleIQ © 2026.

## Support

- **Issues:** GitHub Issues
- **Slack:** #mantleiq-dev
- **Email:** team@mantleiq.com

---

**Last Updated:** 2026-05-10  
**Status:** MVP Phase 1 - Data Ingestion
