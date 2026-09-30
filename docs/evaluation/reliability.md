# Reliability and failure handling

Automated checks cover malformed Pub/Sub envelopes, invalid event fields, duplicate alert delivery, threshold/no-alert paths, notification failure visibility, stale state, Gemini fallback, invalid request data, missing risk features, invalid coordinates, and scenario validation.

The event handler uses derived alert IDs to suppress unchanged duplicate conditions in the running service. Notification failure does not mark the receipt as sent; Eventarc ingress returns `503` so a managed platform can retry. The current receipt store is process-local, so durable cross-instance deduplication remains a production limitation.
