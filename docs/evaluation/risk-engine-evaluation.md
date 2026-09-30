# Risk engine evaluation

The Phase 3 risk engine remains unchanged. It calculates a transparent 0-100 score from wind, rainfall, track proximity, low-elevation susceptibility, and population exposure. Tests verify deterministic outputs, contribution sums, required-feature rejection, score bounds under extreme inputs, and high-band threshold behavior.

Representative persisted results and contribution values are in [results.json](results.json). The risk formula is a demonstration baseline, not a calibrated impact model; a high score is a decision-support signal, not an official warning.
