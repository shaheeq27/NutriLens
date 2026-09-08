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
enforced in the response contract itself, not just by convention — see
`backend/app/contracts/scan_contract.py` once it exists.

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
│       └── test_scan_api.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── postcss.config.mjs
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

## Build status

This project is being built one file at a time, in this order. Unchecked
items don't exist yet.

- [x] `README.md`
- [ ] `.gitignore`
- [ ] `.env.example`
- [ ] `backend/pyproject.toml`
- [ ] `backend/requirements.txt`
- [ ] `backend/app/__init__.py`
- [ ] `backend/app/core/config.py`
- [ ] `backend/app/contracts/scan_contract.py`
- [ ] `backend/tests/test_scan_contract.py`
- [ ] `backend/app/services/image_validation.py`
- [ ] `backend/app/services/photo_privacy.py`
- [ ] `backend/tests/test_image_validation.py`
- [ ] `backend/tests/test_photo_privacy.py`
- [ ] `backend/app/providers/openai_vision.py`
- [ ] `backend/app/providers/google_vision.py`
- [ ] `backend/app/providers/usda_fooddata.py`
- [ ] `backend/app/services/food_recognition.py`
- [ ] `backend/app/services/label_ocr.py`
- [ ] `backend/app/services/nutrition_lookup.py`
- [ ] `backend/app/services/scan_orchestrator.py`
- [ ] `backend/app/api/routes/health.py`
- [ ] `backend/app/api/routes/scan.py`
- [ ] `backend/app/main.py`
- [ ] `backend/tests/test_scan_api.py`
- [ ] `frontend/package.json`
- [ ] `frontend/tsconfig.json`
- [ ] `frontend/next.config.ts`
- [ ] `frontend/postcss.config.mjs`
- [ ] `frontend/src/app/globals.css`
- [ ] `frontend/src/app/layout.tsx`
- [ ] `frontend/src/contracts/scan_contract.ts`
- [ ] `frontend/tests/scan_contract.test.ts`
- [ ] `frontend/src/lib/api.ts`
- [ ] `frontend/src/components/ImageUploader.tsx`
- [ ] `frontend/src/components/ScanProgress.tsx`
- [ ] `frontend/src/components/ScanResult.tsx`
- [ ] `frontend/src/components/ErrorState.tsx`
- [ ] `frontend/src/app/page.tsx`
- [ ] `frontend/src/app/scan/page.tsx`
- [ ] `frontend/src/app/result/page.tsx`

## Getting started

Setup instructions will be added here once `backend/requirements.txt` /
`backend/pyproject.toml` and `frontend/package.json` exist.