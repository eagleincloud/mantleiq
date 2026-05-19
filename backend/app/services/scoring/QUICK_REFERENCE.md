# Scoring Service - Quick Reference

## Import

```python
from app.services.scoring import (
    RuleScorer, EnsembleScorer, 
    FeatureScores, ConfidenceComponents
)
```

## Initialize

```python
import yaml

with open("config/model.yaml") as f:
    config = yaml.safe_load(f)

rule_scorer = RuleScorer(config)
ensemble_scorer = EnsembleScorer(config, rule_scorer)
```

## Quick Score

```python
# Create features
features = FeatureScores(
    fault_intersection=0.8,
    ultramafic_proximity=0.5,
    gravity_anomaly=0.6,
    magnetic_anomaly=0.7,
    heat_flow_indicator=0.5,
    structural_complexity=0.4,
    seep_proximity=0.2,
)

# Score
result = ensemble_scorer.score(features, ml_score=0.75)

print(f"Score: {result.final_score:.3f}")
print(f"Rank: {result.final_rank}th percentile")
```

## With Confidence

```python
confidence = ConfidenceComponents(
    data_coverage=0.8,      # 80% of data available
    data_quality=0.7,       # Quality [0, 1]
    missing_completeness=0.9 # Inverse of missing data
)

result = ensemble_scorer.score(features, ml_score=0.75, confidence_components=confidence)
```

## From Dict

```python
feature_dict = {
    "fault_intersection": 0.8,
    "gravity_anomaly": 0.6,
    "heat_flow_indicator": 0.5,
    # ... other features default to 0.5
}

result = ensemble_scorer.score_dict(
    feature_dict=feature_dict,
    ml_score=0.75,
    coverage=0.8,
    quality=0.7,
    completeness=0.9
)
```

## Explain

```python
explanation = ensemble_scorer.explain_score(result)

print(f"Score: {explanation['final_score']}")
print(f"Rank: {explanation['final_rank']}th percentile")
print(f"Top factors: {explanation['top_factors']}")
print(f"Confidence: {explanation['confidence']}")
print(f"Caveats: {explanation['confidence_notes']}")
```

## Batch Processing

```python
features_list = [
    {"fault_intersection": 0.8, ...},
    {"fault_intersection": 0.5, ...},
    {"fault_intersection": 0.2, ...},
]

results = []
for feature_dict in features_list:
    result = ensemble_scorer.score_dict(feature_dict)
    results.append({
        "cell_id": feature_dict["cell_id"],
        "score": result.final_score,
        "rank": result.final_rank,
        "confidence": result.confidence_adjusted,
    })
```

## In FastAPI Endpoint

```python
from fastapi import APIRouter
from app.services.scoring import EnsembleScorer
from app.core.config import Settings

router = APIRouter()
config = Settings()
rule_scorer = RuleScorer(config.model_config)
ensemble = EnsembleScorer(config.model_config, rule_scorer)

@router.get("/zones/{zone_id}")
async def get_zone(zone_id: str):
    # Load features from DB
    features = load_features_from_db(zone_id)
    
    # Score
    result = ensemble.score(features)
    
    # Explain
    explanation = ensemble.explain_score(result)
    
    return {
        "zone_id": zone_id,
        "final_score": result.final_score,
        "final_rank": result.final_rank,
        "explanation": explanation,
    }
```

## Score Breakdown

Result object contains:
- `rule_score` — pure rule-based [0, 1]
- `ml_score` — ML prediction or None
- `ensemble_score` — hybrid before confidence
- `confidence_adjusted` — modifier [0.5, 1.0]
- `final_score` — ensemble × confidence [0, 1]
- `final_rank` — percentile [0-100]
- `rule_components` — {factor_name: weighted_value}
- `confidence_components` — {coverage, quality, completeness}

## Normalization Utilities

```python
from app.services.scoring import (
    clamp01, linear_normalize, 
    inverse_distance_weight, sigmoid_normalize
)

clamp01(2.5)                           # 1.0
linear_normalize(50, 0, 100)           # 0.5
inverse_distance_weight(50, 100)       # 0.5
sigmoid_normalize(0.7, midpoint=0.5)   # ~0.73
```

## Testing

```python
# All scoring functions are tested
# Run: python3 backend/tests/test_scoring_service.py

# Expected output:
# ✓ Testing clamp01...
# ✓ Testing linear_normalize...
# ✓ Testing inverse_distance_weight...
# ✓ Testing RuleScorer...
# ✓ Testing EnsembleScorer...
# ✓ Testing score explanation...
# ✅ All tests passed!
```

---

**Full API:** See `SCORING_SERVICE_GUIDE.md`  
**Config:** See `config/model.yaml`
