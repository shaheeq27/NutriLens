# NutriLens Project Brief - §9 Update

## 9. Contract Design (Updated)

The backend and frontend communicate via a strict 9-state discriminated union on the `status` field. 

### Core Guarantees:
- **`extra="forbid"`**: Unknown fields will actively fail validation.
- **Bounded lengths**: String limits (`max_length`) and list limits enforce safety and prevent DoS.
- **Explicit nullables**: Required fields that can be null must be `Optional[X] = None`.
- **Provenance Safety**: `NutritionResult.source` is its own discriminated union (`UsdaSource | LabelSource`). A USDA result cannot contain `ocr_confidence`, and a label result cannot contain an `fdc_id`.

### The 9 States:
1. `image_rejected` (requires `reason`)
2. `no_food_detected`
3. `raw_food_detected` (requires `candidates` list)
4. `package_detected`
5. `label_ocr_extracted` (requires `raw_text_snippet`)
6. `ocr_validation_failed` (requires `missing_fields` list)
7. `nutrition_result` (requires `food_name`, `source` union)
8. `nutrition_not_found` (requires `item_name`)
9. `error` (requires `message`)

*Lanes B & C: Build against this structure exactly.*
