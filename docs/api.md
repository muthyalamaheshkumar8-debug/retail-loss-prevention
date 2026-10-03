# API

Interactive reference is available at `http://localhost:8080/api/docs` (proxied to FastAPI). Login from the app first; protected requests use the HttpOnly session cookie. Mutations must come from APP_ORIGIN if an Origin header is present.

| Method | Path | Purpose |
|---|---|---|
| POST | /api/auth/login, /api/auth/logout | Session lifecycle |
| GET | /api/auth/me | Current account |
| GET/POST | /api/users | Admin user management |
| PATCH | /api/users/{id}/disabled?disabled=true | Disable / enable an account |
| GET/POST | /api/stores | Stores/cameras |
| PUT | /api/stores/{id} | Admin edits a store |
| POST | /api/videos/upload | Multipart file, store_id, camera_id |
| GET | /api/videos?page=1 | Paginated video library |
| GET | /api/videos/{id} | Metadata and job status |
| POST | /api/videos/{id}/process | Queue zones and detect=true/false |
| GET | /api/videos/{id}/events?page=1 | Neutral observations |
| GET | /api/videos/{id}/media?variant=playback | original/playback/overlay with Range |
| GET/POST | /api/incidents | Filtered list / human creates incident |
| GET | /api/incidents/{id} | Incident and video context |
| POST | /api/incidents/{id}/opened | Access audit |
| PATCH | /api/incidents/{id} | Submit versioned review (alias) |
| POST | /api/incidents/{id}/review | Submit status, notes and current version |
| PATCH | /api/incidents/{id}/assignment | Admin sets reviewer_id and version |
| GET | /api/incidents/{id}/audit | Embedded history + access audit |
| GET | /api/incidents/{id}/evidence/clip | Authenticated MP4 |
| GET | /api/incidents/{id}/evidence/thumbnail | Authenticated JPEG |
| POST | /api/incidents/{id}/evidence/retry | Requeue failed evidence |
| GET | /api/incidents/{id}/report?format=pdf | PDF or JSON |
| GET | /api/investigations | Latest 100 reviewed cases |
| GET | /api/analytics/summary | KPIs + charts, scoped cases |
| GET | /api/reports/incidents.csv | All accessible incidents as CSV |
| GET | /api/settings, /api/health | Capabilities / database health |

Incident filters: search, status, category, store_id, camera_id, date (YYYY-MM-DD UTC), reviewer_id, page. Lists return `{items,total,page}`. IDs are opaque strings. Status transitions remain human decisions; version mismatch returns 409. Invalid files/fields return 422, oversized files 413, unauthorized access 401/403, and database outages 503.
