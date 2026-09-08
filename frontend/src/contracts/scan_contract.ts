/**
 * Scan response contract — mirrors backend/app/contracts/scan_contract.py
 * exactly. Generated to match; do not maintain independently. Regenerate
 * from the Python source of truth whenever it changes.
 *
 * Path in repo: frontend/src/contracts/scan_contract.ts
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Shared building blocks
// ---------------------------------------------------------------------------

export const QuantitySchema = z
  .object({
    amount: z.number().gt(0).lte(100_000),
    unit: z.string().min(1).max(32),
  })
  .strict();
export type Quantity = z.infer<typeof QuantitySchema>;

export const NutrientsSchema = z
  .object({
    calories_kcal: z.number().min(0).max(10_000),
    protein_g: z.number().min(0).max(1_000),
    carbohydrates_g: z.number().min(0).max(1_000),
    fat_g: z.number().min(0).max(1_000),
    fiber_g: z.number().min(0).max(1_000).nullable().optional(),
    sugar_g: z.number().min(0).max(1_000).nullable().optional(),
    sodium_mg: z.number().min(0).max(100_000).nullable().optional(),
  })
  .strict();
export type Nutrients = z.infer<typeof NutrientsSchema>;

export const FoodCandidateSchema = z
  .object({
    food_name: z.string().min(1).max(128),
    confidence: z.number().min(0).max(1),
  })
  .strict();
export type FoodCandidate = z.infer<typeof FoodCandidateSchema>;

// ---------------------------------------------------------------------------
// Nutrition source — mutually exclusive at the type level (the core rule)
// ---------------------------------------------------------------------------

export const UsdaSourceSchema = z
  .object({
    source: z.literal("usda"),
    fdc_id: z.string().min(1).max(64),
    usda_description: z.string().min(1).max(256),
  })
  .strict();

export const LabelSourceSchema = z
  .object({
    source: z.literal("label"),
    ocr_confidence: z.number().min(0).max(1),
  })
  .strict();

export const NutritionSourceSchema = z.discriminatedUnion("source", [
  UsdaSourceSchema,
  LabelSourceSchema,
]);
export type NutritionSource = z.infer<typeof NutritionSourceSchema>;

// ---------------------------------------------------------------------------
// Response states — discriminated union on `status`
// ---------------------------------------------------------------------------

export const ImageRejectedSchema = z
  .object({
    status: z.literal("image_rejected"),
    reason: z.enum([
      "file_too_large",
      "unsupported_file_type",
      "invalid_magic_bytes",
      "dimensions_out_of_range",
      "megapixel_limit_exceeded",
      "decode_timeout",
    ]),
  })
  .strict();

export const NoFoodDetectedSchema = z
  .object({
    status: z.literal("no_food_detected"),
  })
  .strict();

export const RawFoodDetectedSchema = z
  .object({
    status: z.literal("raw_food_detected"),
    food_name: z.string().min(1).max(128),
    candidates: z.array(FoodCandidateSchema).max(5).default([]),
    suggested_quantity: QuantitySchema,
  })
  .strict();

export const PackageDetectedSchema = z
  .object({
    status: z.literal("package_detected"),
    product_guess: z.string().max(128).nullable().optional(),
  })
  .strict();

export const LabelOcrExtractedSchema = z
  .object({
    status: z.literal("label_ocr_extracted"),
    raw_fields: z
      .record(z.string(), z.string())
      .refine((obj) => Object.keys(obj).length <= 50, {
        message: "raw_fields cannot have more than 50 keys",
      })
      .default({}),
  })
  .strict();

export const OcrValidationFailedSchema = z
  .object({
    status: z.literal("ocr_validation_failed"),
    reason: z.enum(["unreadable", "incomplete", "inconsistent_values"]),
    missing_fields: z.array(z.string()).max(20).default([]),
  })
  .strict();

export const NutritionResultSchema = z
  .object({
    status: z.literal("nutrition_result"),
    food_name: z.string().min(1).max(128),
    quantity: QuantitySchema,
    nutrients: NutrientsSchema,
    source: NutritionSourceSchema,
  })
  .strict();

export const NutritionNotFoundSchema = z
  .object({
    status: z.literal("nutrition_not_found"),
    food_name: z.string().min(1).max(128),
  })
  .strict();

export const ScanErrorSchema = z
  .object({
    status: z.literal("error"),
    message: z.string().min(1).max(512),
    retryable: z.boolean(),
  })
  .strict();

export const ScanResponseSchema = z.discriminatedUnion("status", [
  ImageRejectedSchema,
  NoFoodDetectedSchema,
  RawFoodDetectedSchema,
  PackageDetectedSchema,
  LabelOcrExtractedSchema,
  OcrValidationFailedSchema,
  NutritionResultSchema,
  NutritionNotFoundSchema,
  ScanErrorSchema,
]);

export type ScanResponse = z.infer<typeof ScanResponseSchema>;
