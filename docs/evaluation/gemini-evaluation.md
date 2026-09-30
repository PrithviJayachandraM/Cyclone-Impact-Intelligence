# Grounded assistant evaluation

The golden set covers risk explanation, highest exposure, situation summary, observed-versus-forecast context, timestamp/source context, scenario explanation, and an unsupported bridge question. Each answer is evaluated against a controlled backend context, not tone alone. Results are written to [gemini-golden-set.json](gemini-golden-set.json).

The deterministic local responder is evaluated by default. Vertex Gemini is not executed without configured credentials. The assistant is not authoritative for scores, forecasts, or alerts: structured data and deterministic components remain authoritative. Unsupported information returns a bounded uncertainty response.
