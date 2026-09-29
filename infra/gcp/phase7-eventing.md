# Phase 7 eventing deployment

Phase 7 uses this production path:

```text
Cloud Scheduler -> POST /alerts/trigger -> Pub/Sub topic -> Eventarc -> POST /events/pubsub
    -> Cloud Run alert workflow -> Firebase Cloud Messaging
```

The application selects the local adapters by default. For Google Cloud deployment, set `ALERT_EVENT_TRANSPORT=pubsub` and `NOTIFICATION_PROVIDER=firebase`, then provide the identifiers and runtime-only access tokens documented in `.env.example` through Secret Manager or the service runtime. Do not commit tokens.

An authorized project administrator must create the Pub/Sub topic, deploy the Cloud Run service with IAM authentication enabled, route the topic to `/events/pubsub` through Eventarc, and create a Scheduler HTTP job that invokes `/alerts/trigger` with an OIDC service account. The Scheduler service account needs only permission to invoke this Cloud Run service. The Pub/Sub publisher needs only topic publishing permission. Eventarc needs permission to invoke the event receiver. The Cloud Run service identity needs only the data-read and Firebase Messaging permissions it uses.

The Scheduler request body is the validated event schema below; `event_id` makes retries traceable.

```json
{
  "event_id": "scheduler-risk-2026-01-01T00-00-00Z",
  "cyclone_id": "phailin-2013",
  "valid_time": "2013-10-13T00:00:00Z"
}
```

For local development, leave both providers as `local`, run the application, and use `POST /alerts/trigger` or the **Run local risk evaluation** dashboard button. The in-process publisher immediately invokes the same alert workflow; `POST /events/pubsub` accepts an Eventarc-style Pub/Sub envelope for integration testing.
