/**
 * Tests for frontend/src/contracts/scan_contract.ts.
 * Path in repo: frontend/tests/scan_contract.test.ts
 */

import { ScanResponseSchema } from "../src/contracts/scan_contract";

const validSamples: Record<string, unknown> = {
  image_rejected: { status: "image_rejected", reason: "file_too_large" },
  no_food_detected: { status: "no_food_detected" },
  raw_food_detected: {
    status: "raw_food_detected",
    food_name: "banana",
    candidates: [{ food_name: "plantain", confidence: 0.2 }],
    suggested_quantity: { amount: 1, unit: "medium" },
  },
  package_detected: { status: "package_detected", product_guess: "protein bar" },
  label_ocr_extracted: {
    status: "label_ocr_extracted",
    raw_fields: { calories: "210" },
  },
  ocr_validation_failed: {
    status: "ocr_validation_failed",
    reason: "incomplete",
    missing_fields: ["protein_g"],
  },
  nutrition_result: {
    status: "nutrition_result",
    food_name: "banana",
    quantity: { amount: 118, unit: "g" },
    nutrients: {
      calories_kcal: 105,
      protein_g: 1.3,
      carbohydrates_g: 27,
      fat_g: 0.4,
    },
    source: {
      source: "usda",
      fdc_id: "173944",
      usda_description: "Bananas, raw",
    },
  },
  nutrition_not_found: {
    status: "nutrition_not_found",
    food_name: "dragonfruit smoothie",
  },
  error: { status: "error", message: "vendor timeout", retryable: true },
};

let failures = 0;

function check(label: string, condition: boolean): void {
  if (condition) {
    console.log(`OK   ${label}`);
  } else {
    console.log(`FAIL ${label}`);
    failures++;
  }
}

for (const [status, payload] of Object.entries(validSamples)) {
  const result = ScanResponseSchema.safeParse(payload);
  check(`valid state round-trips: ${status}`, result.success);
}

check(
  "unknown field rejected",
  !ScanResponseSchema.safeParse({ status: "no_food_detected", extra_junk: "nope" })
    .success
);

check(
  "unknown status rejected",
  !ScanResponseSchema.safeParse({ status: "not_a_real_status" }).success
);

check(
  "usda and label fields cannot mix",
  !ScanResponseSchema.safeParse({
    status: "nutrition_result",
    food_name: "banana",
    quantity: { amount: 118, unit: "g" },
    nutrients: {
      calories_kcal: 105,
      protein_g: 1.3,
      carbohydrates_g: 27,
      fat_g: 0.4,
    },
    source: {
      source: "usda",
      fdc_id: "173944",
      usda_description: "Bananas, raw",
      ocr_confidence: 0.9, // label-only field, must be rejected
    },
  }).success
);

check(
  "candidates list bounded",
  !ScanResponseSchema.safeParse({
    status: "raw_food_detected",
    food_name: "banana",
    candidates: Array.from({ length: 6 }, (_, i) => ({
      food_name: `item${i}`,
      confidence: 0.1,
    })),
    suggested_quantity: { amount: 1, unit: "medium" },
  }).success
);

check(
  "negative nutrient value rejected",
  !ScanResponseSchema.safeParse({
    status: "nutrition_result",
    food_name: "banana",
    quantity: { amount: 118, unit: "g" },
    nutrients: {
      calories_kcal: -5,
      protein_g: 1.3,
      carbohydrates_g: 27,
      fat_g: 0.4,
    },
    source: {
      source: "usda",
      fdc_id: "173944",
      usda_description: "Bananas, raw",
    },
  }).success
);

if (failures > 0) {
  console.error(`\n${failures} check(s) failed`);
  process.exit(1);
} else {
  console.log("\nAll checks passed");
}
