# NutriLens — Shared Project Brief

Paste this whole document as the first message in any Claude session working
on this repo. It exists because chat transcripts between sessions drift from
what's actually committed — this doc plus the live GitHub repo are the only
two sources of truth. Chat history from another account is not.

Repo: https://github.com/shaheeq27/NutriLens

---

## 1. What NutriLens is

A mobile-first web app that takes a food photo and returns trustworthy
nutrition information. Two flows:

- **Raw food** (fruit, veg, meat, dairy, grains, etc.) — vision model
  identifies the food → user confirms/adjusts quantity → nutrition comes
  from **USDA FoodData Central**.
- **Packaged food** (biscuits, snacks, drinks) — system detects it's a
  package → asks for a photo of the back/side nutrition label → OCR reads
  it → extracted values are validated before display.

## 2. The one non-negotiable rule

**The vision model identifies food. It never invents nutrition numbers.**

Raw-food nutrition always comes from USDA FoodData Central. Packaged-food
nutrition always comes from the OCR'd label. This is enforced by the
response *contract* (a discriminated union — see §9), not just by
convention. No code path should let a model estimate a nutrition value.

## 3. V1 scope

**In scope:** one visible food item per scan; raw-food ID + quantity +
DB lookup; packaged-food detection + label OCR + validated extraction;
image validation before any vendor API call (size, type, magic bytes,
dimensions, megapixel limit, decode timeout); EXIF stripping; no raw
image/OCR-text logging; no permanent photo storage; mock providers first,
real APIs wired in after.

**Out of scope:** mixed meals/thalis/multi-food plates; cooked dishes with
unknown recipe/oil/method; accounts/login/history; payments; native
mobile apps; barcode scanning; calorie tracking; meal plans.

## 4. Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS, Zod |
| Backend | Python, FastAPI, Pydantic v2 |
| Vision | OpenAI vision-capable model |
| OCR | Google Cloud Vision |
| Nutrition data | USDA FoodData Central |
| Testing | Pytest (backend), TypeScript runtime tests (frontend) |
| Deployment (later) | Vercel (frontend), Google Cloud Run (backend) |

## 5. Architecture rules (hold across every file)

- `backend/app/contracts/scan_contract.py` is the backend source of truth
  for the response contract.
- `frontend/src/contracts/scan_contract.ts` mirrors it exactly, validated
  at runtime with Zod — it's *generated to match* the backend, never
  maintained independently.
- Raw-food results carry USDA-sourced values; packaged-food results carry
  label-sourced values. Mutually exclusive by construction, not by two
  fields happening to agree.
- Every uploaded image is validated (size, type, magic bytes, dimensions,
  megapixel limit, decode timeout) before any vendor API call.
- EXIF stripped on ingest. Raw image bytes and raw OCR text are never
  logged. No permanent photo storage in V1.
- Contract models reject unknown fields; string/list lengths are bounded.
- Nullable fields are explicit and consistent between Python and
  TypeScript.
- Providers are mocked first; real external APIs wired in only after the
  mocked path is tested.

## 6. Verified real repo state (checked directly against GitHub, not trusted from any chat)

This matters because it has already diverged from what one session
*believed* was true. Always re-verify against the live repo before
trusting a summary — including this one, if time has passed.

**Actually correct and committed:**
- `.gitignore` — real, matches the rules above.
- `backend/pyproject.toml` — real: fastapi, pydantic v2, pydantic-settings,
  python-multipart, Pillow, httpx, openai, google-cloud-vision, plus
  pytest/pytest-asyncio dev deps.
- `backend/requirements.txt` — fixed to mirror pyproject.toml exactly.
- `.env.example` — fixed: `OPENAI_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`,
  `USDA_FDC_API_KEY`, `BACKEND_PORT`, `NEXT_PUBLIC_API_URL`.

**Stale placeholders — look real but must be fully rebuilt, not extended:**
- `backend/app/contracts/scan_contract.py` — currently a flat single
  `ScanResponse` model (`food_name`, `calories`, `nutrients: list[...]`).
  Does **not** implement the discriminated union or the raw/packaged
  separation. Needs a full rebuild per §9 below.
- `backend/app/core/config.py` — currently loads a `gemini_api_key` field
  left over from an earlier, abandoned provider decision. Needs rebuild to
  load the four vars now in `.env.example` via `pydantic-settings`.

**Doesn't exist yet:** everything else in the checklist, including
`backend/app/__init__.py`.

**Before starting any file:** fetch its current raw content from
`https://raw.githubusercontent.com/shaheeq27/NutriLens/main/<path>` to see
what's really there. Don't assume the checklist or a prior session's
description is accurate.

## 7. Working rules for all three lanes

1. Only touch files in your own lane (§10). If you think a file in another
   lane needs to change, say so in your response — don't edit it.
2. Before starting a file, pull its current state from GitHub (§6 method).
3. After finishing a file: commit, push, and update its checkbox in this
   repo's `README.md` "Build status" section in the same commit. That
   checklist is the shared ledger — not chat transcripts pasted between
   accounts.
4. If a file you need (e.g. the contract) doesn't exist yet in the repo,
   build against the **frozen spec in §9** below rather than waiting —
   that's the whole point of freezing it up front.
5. Flag, don't silently resolve, any place where reality (§6) conflicts
   with this brief or with another lane's assumed output.

## 8. Why three lanes, not a strict file-by-file queue

The original plan built one file at a time in checklist order. That
doesn't parallelize across three accounts. Instead, work is split by
**layer**, with the one real cross-layer dependency (the contract shape)
frozen in writing below so no lane has to wait on another lane's actual
code.

## 9. Frozen contract specification (DRAFT — build against this; flag if it needs to change)

This is a proposed shape based on the flows in §1–2, not a previously
verified file (the "9-state" design described in an earlier chat did not
match what's actually in the repo — see §6). Lane A codes this into real
Pydantic/Zod; Lanes B and C can build against the shape below immediately
without waiting for Lane A's file to land.

A scan response is a discriminated union on a `status` field:

| `status` | Meaning | Key fields |
|---|---|---|
| `image_rejected` | Failed validation before any vendor call | `reason` (size/type/magic-bytes/dimensions/decode) |
| `no_food_detected` | Vision model found no identifiable food in frame | — |
| `raw_food_detected` | Vision identified a raw food; awaiting quantity confirm | `food_name`, `candidates?`, `suggested_quantity` |
| `package_detected` | Image is a packaged product; label photo needed | `product_guess?` |
| `label_ocr_extracted` | OCR ran but extraction needs validation before showing | `raw_fields` (pre-validation) |
| `ocr_validation_failed` | Label unreadable/incomplete/inconsistent | `reason`, `missing_fields?` |
| `nutrition_result` | **Final result**, either path converges here | `source: "usda" \| "label"`, `food_name`, `quantity`, `nutrients` (calories, protein, carbs, fat, etc.) |
| `nutrition_not_found` | Raw food identified, no USDA match — hard stop, never estimate | `food_name` |
| `error` | Generic/vendor failure | `message`, `retryable: bool` |

Rules that must hold in the real implementation:
- `nutrition_result.source` determines which fields are populated —
  USDA-path and label-path results are mutually exclusive at the type
  level (e.g. via a nested discriminated union on `source`), not just two
  optional fields that happen to agree.
- Every state model rejects unknown fields (`model_config = {"extra": "forbid"}`
  in Pydantic; `.strict()` / no passthrough in Zod).
- String/list fields have explicit max lengths.
- Nullable fields must be `Optional[X] = None` in Python and `X | null`
  (with matching `.nullable()` / `.optional()` semantics) in Zod — decide
  once per field and keep both sides consistent.

**If Lane A finalizes something different from this table, Lane A must
post the actual field list back so Lanes B/C can reconcile** — this table
is a starting point to unblock parallel work, not a permanent spec.

## 10. Three-lane split (zero file overlap)

### Lane A — Contracts & Core Foundation
Owns the interface everything else depends on, plus app bootstrapping.

- `backend/app/contracts/scan_contract.py` (full rebuild, §9)
- `frontend/src/contracts/scan_contract.ts` (mirrors the above — **Lane A
  owns this even though it's physically inside `frontend/`**)
- `backend/tests/test_scan_contract.py`
- `frontend/tests/scan_contract.test.ts`
- `backend/app/__init__.py`
- `backend/app/core/config.py` (rebuild — load the four real env vars via pydantic-settings)
- `backend/app/core/logging.py`
- `backend/app/utils/errors.py`
- Ownership/maintenance of `.env.example`, `.gitignore`, `backend/pyproject.toml`, `backend/requirements.txt` going forward

**Priority:** finish `scan_contract.py`/`.ts` first and post the real
field list back, since Lanes B and C's *last* files depend on it (see
below). Everything else in Lane A has no cross-lane dependency.

### Lane B — Backend business logic
Owns everything that turns a photo into a contract response.

- `backend/app/providers/openai_vision.py`
- `backend/app/providers/google_vision.py`
- `backend/app/providers/usda_fooddata.py`
- `backend/app/services/image_validation.py`
- `backend/app/services/photo_privacy.py`
- `backend/app/services/food_recognition.py`
- `backend/app/services/label_ocr.py`
- `backend/app/services/nutrition_lookup.py`
- `backend/app/services/scan_orchestrator.py` — **build this last**; it's
  the one file that assembles the actual contract response
- `backend/app/api/routes/health.py`
- `backend/app/api/routes/scan.py` — **build this last**, same reason
- `backend/app/main.py`
- `backend/tests/test_image_validation.py`
- `backend/tests/test_photo_privacy.py`
- `backend/tests/test_scan_api.py`

Providers, `image_validation.py`, and `photo_privacy.py` have **zero**
dependency on the contract shape — start there immediately.

### Lane C — Frontend
Owns the UI shell and everything under `frontend/` except the contract file.

- `frontend/package.json`, `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`
- `frontend/src/app/globals.css`, `layout.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/components/ImageUploader.tsx`
- `frontend/src/components/ScanProgress.tsx`
- `frontend/src/components/ErrorState.tsx`
- `frontend/src/components/ScanResult.tsx` — **build last**; renders the
  `nutrition_result` / `nutrition_not_found` states directly
- `frontend/src/app/page.tsx`, `scan/page.tsx`
- `frontend/src/app/result/page.tsx` — **build last**, same reason

Config files, layout, `ImageUploader`, and `ScanProgress` have no contract
dependency — start there immediately.

## 11. Full checklist, tagged by lane

- [x] `README.md`
- [x] `.gitignore` — *(Lane A owns future edits)*
- [x] `.env.example` — *(Lane A owns future edits)*
- [x] `backend/pyproject.toml` — *(Lane A)*
- [x] `backend/requirements.txt` — *(Lane A)*
- [ ] `backend/app/__init__.py` — **Lane A**
- [ ] `backend/app/core/config.py` — **Lane A** (rebuild)
- [ ] `backend/app/core/logging.py` — **Lane A**
- [ ] `backend/app/contracts/scan_contract.py` — **Lane A** (rebuild, priority)
- [ ] `backend/tests/test_scan_contract.py` — **Lane A**
- [ ] `backend/app/utils/errors.py` — **Lane A**
- [ ] `backend/app/services/image_validation.py` — **Lane B**
- [ ] `backend/app/services/photo_privacy.py` — **Lane B**
- [ ] `backend/tests/test_image_validation.py` — **Lane B**
- [ ] `backend/tests/test_photo_privacy.py` — **Lane B**
- [ ] `backend/app/providers/openai_vision.py` — **Lane B**
- [ ] `backend/app/providers/google_vision.py` — **Lane B**
- [ ] `backend/app/providers/usda_fooddata.py` — **Lane B**
- [ ] `backend/app/services/food_recognition.py` — **Lane B**
- [ ] `backend/app/services/label_ocr.py` — **Lane B**
- [ ] `backend/app/services/nutrition_lookup.py` — **Lane B**
- [ ] `backend/app/services/scan_orchestrator.py` — **Lane B** (last, needs contract)
- [ ] `backend/app/api/routes/health.py` — **Lane B**
- [ ] `backend/app/api/routes/scan.py` — **Lane B** (last, needs contract)
- [ ] `backend/app/main.py` — **Lane B**
- [ ] `backend/tests/test_scan_api.py` — **Lane B**
- [ ] `frontend/package.json` — **Lane C**
- [ ] `frontend/tsconfig.json` — **Lane C**
- [ ] `frontend/next.config.ts` — **Lane C**
- [ ] `frontend/postcss.config.mjs` — **Lane C**
- [ ] `frontend/src/app/globals.css` — **Lane C**
- [ ] `frontend/src/app/layout.tsx` — **Lane C**
- [ ] `frontend/src/contracts/scan_contract.ts` — **Lane A** (not Lane C, despite the path)
- [ ] `frontend/tests/scan_contract.test.ts` — **Lane A**
- [ ] `frontend/src/lib/api.ts` — **Lane C**
- [ ] `frontend/src/components/ImageUploader.tsx` — **Lane C**
- [ ] `frontend/src/components/ScanProgress.tsx` — **Lane C**
- [ ] `frontend/src/components/ScanResult.tsx` — **Lane C** (last, needs contract)
- [ ] `frontend/src/components/ErrorState.tsx` — **Lane C**
- [ ] `frontend/src/app/page.tsx` — **Lane C**
- [ ] `frontend/src/app/scan/page.tsx` — **Lane C**
- [ ] `frontend/src/app/result/page.tsx` — **Lane C** (last, needs contract)
