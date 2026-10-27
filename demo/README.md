# demo

Orthanc (DICOMweb) + core + app as a separate compose project (`oncall-resident`).

```sh
cp .env.example .env          # set TAILSCALE_IP (tailscale ip -4)
./seed/fetch.sh               # public LIDC-IDRI DICOM (see ../DATA_SOURCES.md)
docker compose -p oncall-resident up -d --build
./seed/load.sh                # upload into Orthanc via 127.0.0.1:18042
```

| Service | Host binding | Notes |
|---|---|---|
| app | `$TAILSCALE_IP:13000` | the only port reachable from the tailnet |
| core | `127.0.0.1:18000` | debug; app uses the internal network |
| orthanc | `127.0.0.1:18042` | DICOMweb + REST; DICOM port 4242 not published |

`seed/cases.json` holds **synthetic** order metadata keyed by StudyInstanceUID.
