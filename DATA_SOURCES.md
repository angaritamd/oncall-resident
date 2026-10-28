# Data sources

## DICOM images

| Case | Modality | Source subject | License |
|---|---|---|---|
| DEMO-0001 | DX chest radiograph | LIDC-IDRI-0002 | CC BY 3.0 |
| DEMO-0002 | CT chest | LIDC-IDRI-0957 | CC BY 3.0 |
| DEMO-0003 | CR chest radiograph | LIDC-IDRI-0004 | CC BY 3.0 |
| DEMO-0004 | CT chest | LIDC-IDRI-0078 | CC BY 3.0 |
| DEMO-0005 | CT chest | LIDC-IDRI-0983 | CC BY 3.0 |

Exact Study/Series Instance UIDs: [`demo/seed/manifest.json`](demo/seed/manifest.json).

- **Collection:** LIDC-IDRI, The Cancer Imaging Archive (TCIA). https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX
- **License:** Creative Commons Attribution 3.0 Unported (CC BY 3.0), which allows redistribution with attribution. https://creativecommons.org/licenses/by/3.0/
- **Required citations:**
  - Armato III SG, et al. *Data From LIDC-IDRI* [Data set]. The Cancer Imaging Archive. 2015. https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX
  - Armato III SG, et al. The Lung Image Database Consortium (LIDC) and Image Database Resource Initiative (IDRI): a completed reference database of lung nodules on CT scans. *Medical Physics* 38(2):915–931, 2011. https://doi.org/10.1118/1.3528204
  - Clark K, et al. The Cancer Imaging Archive (TCIA): maintaining and operating a public information repository. *J Digit Imaging* 26(6):1045–1057, 2013. https://doi.org/10.1007/s10278-013-9622-7
- **De-identification:** published de-identified by TCIA (`PatientIdentityRemoved = YES`, empty name, birth date and institution; dates shifted to 2000-01-01). Checked locally on 2026-10-26.
- **Not in git:** files are downloaded by `demo/seed/fetch.sh` from the public TCIA API, and `*.dcm` is blocked by the scanner.
- **Not used:** no generated or synthetic medical images. No images are used as clinical evidence.

## Clinical metadata

`demo/seed/cases.json` is **fully synthetic**. It holds sex and age (the public DICOM leave them empty), the reason for exam, the technologist note and critical flag, the priority, the arrival offset and whether priors are available. It was written for this demo, does not describe what the images show, and belongs to no real person.

## Shift-review seeds (ANG-175, part 1)

- `demo/seed/review_cases.json` (**fully synthetic**, tests only): order metadata for DEMO-0006 (critical, normal-template impression), DEMO-0007 (laterality error) and DEMO-0008 (critical, no draft). DEMO-0001..DEMO-0005 and their metadata are never touched by this file.
- `demo/seed/review_reports.json` (**fully synthetic**): draft reports for DEMO-0006 and DEMO-0007 only (DEMO-0008 intentionally has none). Loaded only via `POST /api/demo/reset-reports?set=review` or directly in `core/tests/test_review.py`; the default `reports.json` seed is unchanged. Like the default seed, these texts do not describe any real images and belong to no real person.
