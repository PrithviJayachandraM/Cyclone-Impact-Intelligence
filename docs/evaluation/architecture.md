# Final architecture story

Cyclone Impact Intelligence is a decision-support prototype. The canonical flow keeps calculated facts separate from generated explanations:

```text
Historical / configured source data
        -> normalized immutable replay
        -> enriched weather, terrain, and exposure features
        -> deterministic risk engine -> observed risk layer
                                      -> Phase 4 forecast layer (explicitly labelled)
                                      -> Phase 6 copied-input simulation comparison
        -> controlled Gemini tool context -> grounded explanation only
        -> dashboard and Phase 7 alert evaluation

Cloud Scheduler -> Pub/Sub -> Eventarc -> Cloud Run alert handler -> Firebase (optional)
```

The local demo uses adapters for the cloud event flow and notification delivery, so its end-to-end result is reproducible without cloud credentials. A production deployment replaces those adapters with the documented GCP resources and least-privilege service identities.

## Trust boundary

- Source records, feature provenance, deterministic risk contributions, timestamps, and simulation deltas are factual application outputs.
- Forecast and simulation outputs are labelled as projections or simulations; neither is an official warning.
- Gemini is not allowed to calculate risk, choose thresholds, or trigger alerts. It can only explain the structured context supplied by approved read-only tools.
- Phase 7 threshold evaluation is deterministic and uses an idempotency receipt to suppress repeated unchanged alert conditions.

## Demonstration boundary

The frozen Phailin replay demonstrates architecture and interaction feasibility, not operational readiness. Live data feeds, complete geographic coverage, observed alert delivery, and production performance remain deployment/evaluation work rather than claims of this demo.
