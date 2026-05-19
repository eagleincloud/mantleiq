# Scoring Service Implementation Guide

**Status:** ✅ Complete and Tested  
**Priority:** Phase 0 / Priority 1  
**Duration:** 1.5 hours (completed)

---

## Overview

The scoring service implements MantleIQ's core prospectivity scoring methodology:

- **Rule-based scoring**: 6-factor weighted model (30/20/20/15/10/5%)
- **Confidence adjustment**: Data quality + coverage penalties
- **Ensemble hybrid**: 60% rule + 40% ML (XGBoost) combination
- **Feature normalization**: Utilities for spatial + raster data

---

## Architecture

```
Scoring Service
├── normalization.py
│   ├── clamp01() - bound values [0,1]
│   ├── linear_normalize() - map [min,max] → [0,1]
│   ├── inverse_distance_weight() - proximity scoring
│   ├── sigmoid_normalize() - S-curve transitions
│   ├── percentile_rank() - distribution-aware scaling
│   ├── log_normalize() - power-law distributions
│   └── handle_missing_data() - graceful NA fallbacks
│
├── rule_scorer.py
│   ├── FeatureScores dataclass
│   │   └── 7 normalized input features
│   ├── RuleBasedScore dataclass
│   │   └── 6 factors + weighted sum
│   └── RuleScorer class
│       └── score() → compute 6 factors from features
│
├── ensemble.py
│   ├── ConfidenceComponents dataclass
│   │   └── coverage, quality, completeness
│   ├── EnsembleScore dataclass
│   │   └── rule/ML/ensemble scores + confidence
│   └── EnsembleScorer class
│       ├── score() → hybrid scoring + confidence
│       ├── score_dict() → convenience method
│       └── explain_score() → human-readable breakdown
│
└── __init__.py
    └── Re-exports all public APIs
```

---

## Core Scoring Formula

### 1. Rule-Based Score (60% weight in ensemble)

**6 Factors** derived from 7 base features:

```
F_generation = avg(fault_intersection, seep_proximity)
F_fluid_interaction = avg(gravity_anomaly, magnetic_anomaly)
F_structural_pathways = avg(fault_intersection, structural_complexity)
F_trap_retention = avg(structural_complexity, gravity_anomaly)
F_surface_indicators = seep_proximity
F_thermodynamic = heat_flow_indicator

Score = Σ(weight_i × F_i)  where Σ(weights) = 1.0
```

**Default Weights:**
- F_generation: 0.30 (most important)
- F_fluid_interaction: 0.20
- F_structural_pathways: 0.20
- F_trap_retention: 0.15
- F_surface_indicators: 0.10
- F_thermodynamic: 0.05 (least important)

### 2. Confidence Score

```
confidence_raw = 0.40×data_coverage + 0.40×data_quality + 0.20×missing_completeness
confidence_adjusted = 0.5 + 0.5 × confidence_raw

Result: [0.5, 1.0] where 0.5 = minimal data, 1.0 = complete data
```

### 3. Final Score

```
ensemble_score = 0.60 × rule_score + 0.40 × ml_score
final_score = ensemble_score × confidence_adjusted
final_rank = percentile [0-100]
```

---

## API Reference

### Normalization Functions

#### `clamp01(value: float) → float`
Clamp value to [0, 1] range. Safe for all inputs including NaN.

```python
clamp01(-5)    # 0.0
clamp01(0.5)   # 0.5
clamp01(10)    # 1.0
```

#### `linear_normalize(value, min_val, max_val) → float`
Map [min_val, max_val] → [0, 1] linearly.

```python
linear_normalize(50, 0, 100)   # 0.5
linear_normalize(150, 0, 100)  # 1.0 (clamped)
```

#### `inverse_distance_weight(distance_km, max_distance_km) → float`
Proximity scorer: returns 1.0 at distance=0, 0.0 at max_distance.

```python
inverse_distance_weight(0, 100)    # 1.0
inverse_distance_weight(50, 100)   # 0.5
inverse_distance_weight(100, 100)  # 0.0
```

#### `sigmoid_normalize(value, midpoint=0.5, steepness=10.0) → float`
S-curve transition. Useful for thermodynamic windows.

```python
sigmoid_normalize(0.3, midpoint=0.5)  # ~0.27
sigmoid_normalize(0.5, midpoint=0.5)  # ~0.50
sigmoid_normalize(0.7, midpoint=0.5)  # ~0.73
```

#### `percentile_rank(value, p50, p95) → float`
Rank-based scaling: 0 at p50, 1.0 at p95.

```python
percentile_rank(35, p50=40, p95=80)  # 0.25 (below median)
percentile_rank(60, p50=40, p95=80)  # 0.75 (above median)
```

### RuleScorer Class

#### `RuleScorer(config: dict)`
Initialize with weights from `config/model.yaml`.

```python
config = {
    "weights": {
        "f_generation": 0.30,
        "f_fluid_interaction": 0.20,
        # ... etc
    }
}
scorer = RuleScorer(config)
```

#### `score(features: FeatureScores) → RuleBasedScore`
Compute rule-based score from normalized features.

```python
features = FeatureScores(
    fault_intersection=0.8,
    ultramafic_proximity=0.5,
    gravity_anomaly=0.6,
    magnetic_anomaly=0.7,
    heat_flow_indicator=0.5,
    structural_complexity=0.4,
    seep_proximity=0.2,
)

result = scorer.score(features)
print(f"Score: {result.weighted_score:.3f}")
print(f"Top factor: F_generation = {result.f_generation:.3f}")
```

#### `score_dict(feature_dict: dict) → RuleBasedScore`
Convenience method: score from dict. Missing keys default to 0.5.

```python
feature_dict = {
    "fault_intersection": 0.8,
    "gravity_anomaly": 0.6,
}
result = scorer.score_dict(feature_dict)
```

### EnsembleScorer Class

#### `EnsembleScorer(config: dict, rule_scorer: RuleScorer)`
Initialize hybrid scorer.

```python
config = {
    "weights": { ... },
    "ensemble": {
        "rule_weight": 0.60,
        "ml_weight": 0.40,
    }
}
ensemble = EnsembleScorer(config, rule_scorer)
```

#### `score(features, ml_score=None, confidence_components=None) → EnsembleScore`
Compute hybrid score with confidence adjustment.

```python
confidence = ConfidenceComponents(
    data_coverage=0.8,      # 80% of required layers available
    data_quality=0.7,       # Quality score [0,1]
    missing_completeness=0.9 # 90% of data complete
)

result = ensemble.score(features, ml_score=0.75, confidence_components=confidence)

print(f"Rule score: {result.rule_score:.3f}")
print(f"ML score: {result.ml_score:.3f}")
print(f"Ensemble: {result.ensemble_score:.3f}")
print(f"Confidence: {result.confidence_adjusted:.3f}")
print(f"Final: {result.final_score:.3f}")
print(f"Rank: {result.final_rank}th percentile")
```

#### `score_dict(feature_dict, ml_score=None, coverage=0.7, quality=0.7, completeness=0.8) → EnsembleScore`
Convenience method with simpler arguments.

```python
result = ensemble.score_dict(
    feature_dict={"fault_intersection": 0.8, ...},
    ml_score=0.75,
    coverage=0.8,
    quality=0.7,
    completeness=0.9
)
```

#### `explain_score(score_result: EnsembleScore) → dict`
Generate human-readable score breakdown.

```python
explanation = ensemble.explain_score(result)

print(f"Final Score: {explanation['final_score']}")
print(f"Rank: {explanation['final_rank']}th percentile")
print(f"Top Factors:")
for factor in explanation['top_factors']:
    print(f"  - {factor['factor']}: {factor['percent']:.1f}%")
print(f"Confidence Notes: {explanation['confidence_notes']}")
```

---

## Data Classes

### FeatureScores
7 normalized input features [0, 1]:

```python
@dataclass
class FeatureScores:
    fault_intersection: float          # Density of faults near cell
    ultramafic_proximity: float        # Distance to ultramafic rocks
    gravity_anomaly: float             # Bouguer gravity intensity
    magnetic_anomaly: float            # Magnetic field anomaly
    heat_flow_indicator: float         # Geothermal gradient
    structural_complexity: float       # Fold/fault density
    seep_proximity: float              # Known H2 seeps nearby
```

### RuleBasedScore
Output from RuleScorer:

```python
@dataclass
class RuleBasedScore:
    f_generation: float                # Factor 1 (30%)
    f_fluid_interaction: float         # Factor 2 (20%)
    f_structural_pathways: float       # Factor 3 (20%)
    f_trap_retention: float            # Factor 4 (15%)
    f_surface_indicators: float        # Factor 5 (10%)
    f_thermodynamic: float             # Factor 6 (5%)
    weighted_score: float              # Sum of weighted factors [0,1]
    component_dict: dict               # {factor_name: weighted_value}
```

### ConfidenceComponents
Data quality assessment:

```python
@dataclass
class ConfidenceComponents:
    data_coverage: float               # Fraction [0,1] of required layers
    data_quality: float                # Quality score [0,1]
    missing_completeness: float        # Inverse of missing data fraction
```

### EnsembleScore
Final output from EnsembleScorer:

```python
@dataclass
class EnsembleScore:
    rule_score: float                  # Pure rule-based [0,1]
    ml_score: Optional[float]          # ML prediction or None
    ensemble_score: float              # Hybrid combination [0,1]
    
    confidence_raw: float              # Confidence before modifier
    confidence_adjusted: float         # After modifier [0.5, 1.0]
    confidence_components: ConfidenceComponents
    
    final_score: float                 # ensemble × confidence [0,1]
    final_rank: int                    # Percentile [0-100]
    
    rule_components: dict              # Breakdown of factors
```

---

## Usage Examples

### Example 1: Simple Rule-Based Scoring

```python
from app.services.scoring import RuleScorer, FeatureScores
import yaml

# Load config
with open("config/model.yaml") as f:
    config = yaml.safe_load(f)

# Create scorer
rule_scorer = RuleScorer(config)

# Create features from database or computation
features = FeatureScores(
    fault_intersection=0.8,
    ultramafic_proximity=0.6,
    gravity_anomaly=0.7,
    magnetic_anomaly=0.5,
    heat_flow_indicator=0.6,
    structural_complexity=0.4,
    seep_proximity=0.3,
)

# Score
result = rule_scorer.score(features)
print(f"Rule-based score: {result.weighted_score:.3f}")
```

### Example 2: Ensemble with Confidence

```python
from app.services.scoring import EnsembleScorer, ConfidenceComponents

ensemble = EnsembleScorer(config, rule_scorer)

# Assess data quality for this cell
confidence = ConfidenceComponents(
    data_coverage=0.75,      # Missing gravity data in this region
    data_quality=0.80,       # Good source authority
    missing_completeness=0.85 # Some data gaps
)

# Score with ML prediction from trained model
result = ensemble.score(features, ml_score=0.72, confidence_components=confidence)

print(f"Final score: {result.final_score:.3f}")
print(f"Rank: {result.final_rank}th percentile")
print(f"Confidence: {result.confidence_adjusted:.1%}")
```

### Example 3: Batch Scoring with Dictionary

```python
# In feature engineering pipeline, features stored as dict
features_batch = [
    {"fault_intersection": 0.8, "gravity_anomaly": 0.7, ...},
    {"fault_intersection": 0.4, "gravity_anomaly": 0.5, ...},
    {"fault_intersection": 0.9, "gravity_anomaly": 0.8, ...},
]

scores = []
for feature_dict in features_batch:
    result = ensemble.score_dict(feature_dict, coverage=0.8, quality=0.75)
    scores.append({
        "cell_id": feature_dict["cell_id"],
        "score": result.final_score,
        "rank": result.final_rank,
        "confidence": result.confidence_adjusted,
    })

# Save to database
for score in scores:
    insert_model_output(score)
```

### Example 4: Explainability

```python
result = ensemble.score(features, ml_score=0.75)
explanation = ensemble.explain_score(result)

# Generate narrative for report
narrative = f"""
Zone Score: {explanation['final_score']:.1%} ({explanation['final_rank']}th percentile)

Driven by:
"""
for factor in explanation['top_factors']:
    narrative += f"  - {factor['factor'].replace('_', ' ').title()}: {factor['percent']:.0f}%\n"

narrative += f"\nConfidence: {explanation['confidence']['adjusted']:.0%}\n"
if explanation['confidence_notes']:
    narrative += f"Caveats: {', '.join(explanation['confidence_notes'])}\n"

print(narrative)
```

---

## Integration with FastAPI

### Create Endpoint Handler

```python
# backend/app/api/zones.py

from fastapi import APIRouter, HTTPException
from app.services.scoring import EnsembleScorer, ConfidenceComponents
from app.core.database import SessionLocal
from app.models.schemas import ZoneScoreResponse

router = APIRouter()

@router.get("/zones/{zone_id}/score")
async def get_zone_score(zone_id: str):
    """Get prospectivity score for a zone with confidence."""
    db = SessionLocal()
    
    # Load zone features from DB
    zone_features = db.query(Features).filter_by(zone_id=zone_id).first()
    if not zone_features:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Load ML model (TBD)
    ml_score = None  # model.predict(zone_features.to_array())
    
    # Create ensemble scorer
    ensemble = EnsembleScorer(app_config, rule_scorer)
    
    # Score
    result = ensemble.score(
        features=zone_features.to_feature_scores(),
        ml_score=ml_score,
        confidence_components=zone_features.to_confidence_components()
    )
    
    # Explain
    explanation = ensemble.explain_score(result)
    
    return ZoneScoreResponse(
        zone_id=zone_id,
        final_score=result.final_score,
        final_rank=result.final_rank,
        confidence=result.confidence_adjusted,
        explanation=explanation,
    )
```

---

## Testing

All core scoring functions are tested:

```bash
# Quick validation (no pytest required)
cd backend
python3 tests/test_scoring_service.py

# With pytest (after pip install pytest)
pytest tests/test_scoring_service.py -v
```

Test coverage:
- ✅ Normalization functions (7 functions)
- ✅ Rule-based scoring (mixed/high/low/dict inputs)
- ✅ Ensemble with/without ML
- ✅ Confidence bounds [0.5, 1.0]
- ✅ Final rank [0-100]
- ✅ Score explanation

---

## Priority 2 Tasks (Next)

Once Supabase is configured:

1. **API Endpoints** (2 hours)
   - `/basins` — list available basins
   - `/results/{basin_id}` — fetch pre-computed zone scores
   - `/zones/{zone_id}` — detailed zone + attribution

2. **Feature Engineering Pipeline** (2 hours)
   - Batch compute 25+ features per grid cell
   - Spatial joins with faults, geology, rasters
   - Load into `features` table

3. **Analysis Job Runner** (1 hour)
   - `POST /run-analysis` endpoint
   - Trigger feature compute + scoring
   - Async job tracking

---

**Status:** Scoring service ready for integration with API routes and feature pipeline.
