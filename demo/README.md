# demo

Orthanc (DICOMweb) + core + app as a separate compose project (`oncall-resident`).

```sh
printf 'ORTHANC_USER=oncall\nORTHANC_PASSWORD=%s\nALLOWED_USERS=%s\n' "$(openssl rand -hex 24)" "you@example.com" > .env && chmod 600 .env
./seed/fetch.sh               # public LIDC-IDRI DICOM (see ../DATA_SOURCES.md)
docker compose -p oncall-resident up -d --build
./seed/load.sh                # upload into Orthanc via 127.0.0.1:18042
tailscale serve --bg --https=443 http://127.0.0.1:13000   # HTTPS on the tailnet only (never funnel)
```

| Service | Host binding | Notes |
|---|---|---|
| app | `127.0.0.1:13000` | reachable from the tailnet only via `tailscale serve` (HTTPS 443); requires a `Tailscale-User-Login` in `ALLOWED_USERS` |
| core | `127.0.0.1:18000` | debug; app uses the internal network |
| orthanc | `127.0.0.1:18042` | DICOMweb + REST behind HTTP basic auth (`demo/.env`); DICOM port 4242 not published |

`seed/cases.json` holds **synthetic** order metadata keyed by StudyInstanceUID.

## Hardening

- Every service runs as a non-root user (Orthanc uid 999, core `nobody`, app `node`), with `cap_drop: [ALL]`, `no-new-privileges` and a read-only root filesystem. Only `tmpfs` paths are writable, plus the Orthanc DB volume.
- Base images are pinned by digest (`demo/orthanc/Dockerfile`, `core/Dockerfile`, `app/Dockerfile`).
- The app answers 401 without a tailnet identity and 403 for logins not in `ALLOWED_USERS` (see `app/README.md`). It trusts the `Tailscale-User-Login` header, so the trust boundary is the host plus the core container: the networks are split (`pacs`: orthanc and core; `edge`: core and app), so Orthanc cannot reach the app.
- Orthanc loads only the DICOMweb plugin.
- Orthanc requires basic auth. The core reads `DICOMWEB_USER`/`DICOMWEB_PASSWORD`, and `seed/load.sh` passes the credentials to curl through a temporary config file, never through argv.
- Upgrading an existing volume from the root-owned layout requires a one-off ownership change: `docker run --rm --user root -v oncall-resident_orthanc-db:/db --entrypoint chown oncall-resident-orthanc -R 999:999 /db`
