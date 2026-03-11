# Ops Notes

Operational assumptions currently baked into this repository:

- `obsura-api` health endpoint: `/api/v1/health`
- `obsura-api` production database backend: PostgreSQL
- API writable storage path inside the container: `/var/lib/obsura`
- expected subdirectories on the storage volume: `uploads`, `outputs`
- current proxy target: `127.0.0.1:8000`
- current deployment style: single-host Docker Compose

Watch for image contract changes that would require updates here:

- runtime username or UID/GID changes
- health endpoint changes
- storage root changes
- new mandatory environment variables
- schema upgrade or downgrade constraints
