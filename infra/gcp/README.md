# GCP foundation

Phase 1 uses Cloud Storage for the raw replay CSV, BigQuery GIS for normalized events and track points, and Cloud Run for the read API. Actual project creation, IAM grants, and API enablement require the team-owned project ID and authenticated GCP account, neither of which is present in this repository.

After copying `.env.example` to a local `.env` or exporting the values in a shell, an authorized project administrator can create the named bucket and dataset, run `../bigquery/phase1_schema.sql` after replacing its placeholders, then build and deploy `../cloud-run/Dockerfile`. Use least-privilege service accounts and Secret Manager for any credentials. Do not put service-account JSON or API keys in the repository.
