# NutriLens

NutriLens is a mobile-first web application that scans a photo of food and
returns clear, trustworthy nutrition information.

## What it does

NutriLens supports two scan flows:

**Raw food** — fruits, vegetables, meat, fish, eggs, dairy, grains, pulses,
nuts, and similar minimally processed foods.
1. A vision model identifies the food from the photo.
2. The user confirms or adjusts the quantity.
3. Nutrition values are retrieved from a trusted database — never invented
   by the model.

**Packaged food** — biscuits, snacks, drinks, protein products, and other
items with a printed nutrition label.
1. The system detects that the image is a package.
2. The user is asked for a clear photo of the back/side nutrition label.
3. OCR reads the label, and the extracted values are validated before
   being shown.

## Core rule

**The vision model identifies food. It never invents nutrition numbers.**

Raw-food nutrition always comes from USDA FoodData Central. Packaged-food
nutrition always comes from the OCR'd printed label. This separation is
enforced in the response contract itself.

## V1 scope

V1 focuses on one thing: a single, trustworthy scan.

**In scope:**
- One visible food item per scan (raw or packaged)
- Raw-food identification + user-confirmed quantity + database lookup
- Packaged-food package detection + back-label OCR + validated extraction
- Image validation before any external API call (file size, file type,
  magic bytes, dimensions, megapixel limit, decode timeout)
- EXIF stripping, no raw-image/OCR-text logging, no permanent photo storage
- Mock providers first; real vision/OCR/nutrition APIs connected afterward

**Out of scope for V1:**
- Mixed meals, thalis, or multi-food plates
- Cooked dishes where recipe, oil, or method is unknown
- Accounts, login, or scan history
- Payments
- Native mobile apps
- Barcode scanning, calorie tracking, meal plans

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS, Zod |
| Backend | Python, FastAPI, Pydantic v2 |
| Vision | OpenAI vision-capable model |
| OCR | Google Cloud Vision |
| Nutrition data | USDA FoodData Central |
| Testing | Pytest (backend), TypeScript runtime tests (frontend) |
| Deployment (later) | Vercel (frontend), Google Cloud Run (backend) |

## Project structure

```text
nutrilens/
├── README.md
├── .gitignore
├── .env.example
│
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── logging.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       └── scan.py
│   │   ├── contracts/
│   │   │   └── scan_contract.py
│   │   ├── providers/
│   │   │   ├── openai_vision.py
│   │   │   ├── google_vision.py
│   │   │   └── usda_fooddata.py
│   │   ├── services/
│   │   │   ├── image_validation.py
│   │   │   ├── photo_privacy.py
│   │   │   ├── food_recognition.py
│   │   │   ├── label_ocr.py
│   │   │   ├── nutrition_lookup.py
│   │   │   └── scan_orchestrator.py
│   │   └── utils/
│   │       └── errors.py
│   └── tests/
│       ├── test_scan_contract.py
│       ├── test_image_validation.py
│       ├── test_photo_privacy.py
│       ├── test_scan_api.py
│       ├── test_openai_vision.py
│       ├── test_google_vision.py
│       ├── test_usda_fooddata.py
│       ├── test_food_recognition.py
│       ├── test_label_ocr.py
│       ├── test_nutrition_lookup.py
│       └── test_health.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── postcss.config.mjs
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── scan/
│   │   │   │   └── page.tsx
│   │   │   └── result/
│   │   │       └── page.tsx
│   │   ├── components/
│   │   │   ├── ImageUploader.tsx
│   │   │   ├── ScanProgress.tsx
│   │   │   ├── ScanResult.tsx
│   │   │   └── ErrorState.tsx
│   │   ├── contracts/
│   │   │   └── scan_contract.ts
│   │   └── lib/
│   │       └── api.ts
│   └── tests/
│       └── scan_contract.test.ts
│
└── fixtures/
    ├── raw-food/
    └── packaged-food/
```

## Architecture rules

These hold across every file in this project:

- `backend/app/contracts/scan_contract.py` is the backend source of truth
  for the scan response contract.
- `frontend/src/contracts/scan_contract.ts` mirrors it exactly and
  validates at runtime with Zod — it is generated to match the backend,
  not maintained independently.
- Raw-food results carry USDA-sourced values; packaged-food results carry
  label-sourced values. These are mutually exclusive, not a convention two
  fields happen to agree on.
- Every uploaded image is validated (file size, file type, magic bytes,
  dimensions, megapixel limit, decode timeout) before any vendor API call.
- EXIF metadata is stripped on ingest. Raw image bytes and raw OCR text
  are never logged. Photos are not stored permanently in V1.
- Contract models reject unknown fields; string and list lengths are
  bounded.
- Nullable fields are explicit and consistent between Python and
  TypeScript.
- Providers are mocked first; real external APIs are wired in only after
  the mocked path is tested.
- Backend provider and service behavior has dedicated test coverage under
  `backend/tests/`.
- Additional provider/service tests are intentionally part of Lane B's
  implementation and are not accidental architecture changes.

## Three-lane development model

NutriLens is developed in three parallel lanes with explicit file ownership.

### Lane A — Contracts & Core Foundation

Owns:
- Backend scan contract
- Frontend scan contract
- Contract tests
- Application configuration
- Logging
- Error utilities
- Shared project configuration files

### Lane B — Backend Business Logic

Owns:
- Vision/OCR/nutrition providers
- Image validation and privacy
- Food recognition
- Label OCR
- Nutrition lookup
- Scan orchestration
- Backend API routes
- Backend application entry point
- Backend tests

Lane B also maintains dedicated provider/service tests for non-trivial
provider and business-logic behavior.

### Lane C — Frontend

Owns:
- Next.js application setup
- Global styling and application shell
- API client
- Upload and progress components
- Result and error components
- Scan and result pages

The frontend contract file remains owned by Lane A because it must mirror
the backend contract exactly.

## Build status

The three implementation lanes have completed their assigned files.
The project is now in the integration/reconciliation stage, where the
backend and frontend implementations are verified against the finalized
shared contracts.

### Foundation and configuration

- [x] `README.md`
- [x] `.gitignore`
- [x] `.env.example`
- [x] `backend/pyproject.toml`
- [x] `backend/requirements.txt`
- [x] `backend/app/__init__.py`
- [x] `backend/app/core/config.py`
- [x] `backend/app/core/logging.py`
- [x] `backend/app/utils/errors.py`

### Contracts

- [x] `backend/app/contracts/scan_contract.py`
- [x] `backend/tests/test_scan_contract.py`
- [x] `frontend/src/contracts/scan_contract.ts`
- [x] `frontend/tests/scan_contract.test.ts`

### Backend validation and privacy

- [x] `backend/app/services/image_validation.py`
- [x] `backend/app/services/photo_privacy.py`
- [x] `backend/tests/test_image_validation.py`
- [x] `backend/tests/test_photo_privacy.py`

### Backend providers

- [x] `backend/app/providers/openai_vision.py`
- [x] `backend/tests/test_openai_vision.py`
- [x] `backend/app/providers/google_vision.py`
- [x] `backend/tests/test_google_vision.py`
- [x] `backend/app/providers/usda_fooddata.py`
- [x] `backend/tests/test_usda_fooddata.py`

### Backend services

- [x] `backend/app/services/food_recognition.py`
- [x] `backend/tests/test_food_recognition.py`
- [x] `backend/app/services/label_ocr.py`
- [x] `backend/tests/test_label_ocr.py`
- [x] `backend/app/services/nutrition_lookup.py`
- [x] `backend/tests/test_nutrition_lookup.py`
- [x] `backend/app/services/scan_orchestrator.py`

### Backend API

- [x] `backend/app/api/routes/health.py`
- [x] `backend/app/api/routes/scan.py`
- [x] `backend/app/main.py`
- [x] `backend/tests/test_scan_api.py`
- [x] `backend/tests/test_health.py`

### Frontend setup

- [x] `frontend/package.json`
- [x] `frontend/tsconfig.json`
- [x] `frontend/next.config.ts`
- [x] `frontend/postcss.config.mjs`
- [x] `frontend/tailwind.config.ts`
- [x] `frontend/src/app/globals.css`
- [x] `frontend/src/app/layout.tsx`

### Frontend application

- [x] `frontend/src/lib/api.ts`
- [x] `frontend/src/components/ImageUploader.tsx`
- [x] `frontend/src/components/ScanProgress.tsx`
- [x] `frontend/src/components/ScanResult.tsx`
- [x] `frontend/src/components/ErrorState.tsx`
- [x] `frontend/src/app/page.tsx`
- [x] `frontend/src/app/scan/page.tsx`
- [x] `frontend/src/app/result/page.tsx`

## Current status

All three development lanes have completed their assigned implementation
work.

The next phase is **integration validation**, not parallel feature
development.

The integration pass should verify:

1. The finalized backend contract is the single source of truth.
2. The frontend contract mirrors the backend contract exactly.
3. `scan_orchestrator.py` produces only valid contract responses.
4. `scan.py` exposes those responses without changing their shape.
5. `lib/api.ts` consumes the finalized response contract.
6. `ScanResult.tsx` and `result/page.tsx` handle the actual contract states.
7. Raw-food nutrition values remain USDA-sourced.
8. Packaged-food nutrition values remain label-sourced.
9. No model-generated nutrition values can reach a final nutrition result.
10. Backend and frontend test suites pass against the integrated implementation.

## Getting started

The application is currently in the integration-validation stage.

Setup and run instructions should be finalized against the actual committed
backend and frontend configuration after the three lanes have been reconciled.
