# User guide

1. **Configure and start.** Follow the root README. Sign in with the admin email/password you created locally.
2. **Add sources.** In Stores & cameras, create a store with comma-separated camera names. Settings lets admins create users and disable accounts.
3. **Upload.** Open Video library, choose store/camera and a local MP4, MOV, AVI or MKV. Maximum 500 MB, one hour, 4K input. Footage is stored locally in a Docker volume.
4. **Set zones.** On the video detail screen, add rectangles with x1/y1/x2/y2 fractions of the full frame. The origin is the upper-left corner; `(0,0,1,1)` covers the full image. The coordinate preview shows placement; inspect the original frame to choose boundaries. Use meaningful names such as `checkout` or `entrance`.
5. **Process.** Enable YOLO person tracking for detections, video-local IDs and zone observations. Disable it for conversion-only processing. The page polls job status. Initial model download takes longer. No footage is sent to a hosted model API.
6. **Inspect.** Play the full video or annotated track version, seek with the ±10-second buttons and click timeline observations. Change playback speed with the dropdown. Finished analyses are immutable; upload again to use different zones.
7. **Create a case.** After reviewing footage, enter a timestamp, category, priority and factual notes. Only this human action creates an incident. A worker generates a clip and thumbnail. If evidence generation fails the interface shows an error and retry control.
8. **Review.** Open the incident queue, filter cases, watch surrounding footage and choose an outcome. Every saved note/decision is preserved. Stale submissions are rejected so reviewers cannot silently overwrite each other. Admins can change assignments.
9. **Export.** Each incident offers PDF/JSON reports and a clip download. Reports exports CSV for accessible cases. Analytics updates from saved records, not fabricated demo counts.

Dates are stored as UTC. Date filters use UTC calendar dates; displayed dates/times use the browser's locale. Video timestamps are seconds relative to the uploaded clip, not wall-clock camera timestamps. Audio is intentionally removed during browser normalization.

## Troubleshooting

- **Login fails after editing .env:** bootstrap credentials create only the first admin when the database is empty; editing ADMIN_PASSWORD does not reset an existing account.
- **QUEUED never changes:** run `docker compose logs worker`. The worker must be running alongside the API.
- **FAILED analysis:** inspect the visible error and worker logs. Check available disk/memory, first-run internet/model access and FFmpeg. Requeue a failed video, or turn tracking off to test manual review.
- **Original video will not play:** AVI/MKV and some MOV codecs are not supported by browsers. Run conversion-only processing first. Processed MP4 uses H.264.
- **No observations:** a pretrained model may miss people; zones may not intersect the feet; a rectangle test clip is not a realistic person. This is an honest zero result, not proof of no activity.
- **Cannot save review:** another user changed the record. Copy any unsaved notes, use Load latest review, and submit against the current version.
- **Public hosting:** GitHub stores source code; GitHub Pages cannot host the Python worker and MongoDB. Use a Docker-capable server with the deployment controls in docs/architecture.md.
