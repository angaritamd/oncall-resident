# demo

Orthanc (DICOMweb) + core + app as a separate compose project (`oncall-resident`).

```sh
./seed/fetch.sh               # public LIDC-IDRI DICOM (see ../DATA_SOURCES.md)
docker compose -p oncall-resident up -d --build
./seed/load.sh                # upload into Orthanc via 127.0.0.1:18042
tailscale serve --bg --https=443 http://127.0.0.1:13000   # HTTPS on the tailnet only (never funnel)
```

| Service | Host binding | Notes |
|---|---|---|
| app | `127.0.0.1:13000` | reachable from the tailnet only via `tailscale serve` (HTTPS 443) |
| core | `127.0.0.1:18000` | debug; app uses the internal network |
| orthanc | `127.0.0.1:18042` | DICOMweb + REST; DICOM port 4242 not published |

`seed/cases.json` holds **synthetic** order metadata keyed by StudyInstanceUID.
