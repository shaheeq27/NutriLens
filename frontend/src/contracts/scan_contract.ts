import { z } from "zod";

// -----------------------------------------------------------------------------
// 1. Image Rejected
// -----------------------------------------------------------------------------
export const ImageRejectReasonSchema = z.enum([
  "file_too_large",
  "invalid_format",
  "corrupt_file",
  "dimensions_out_of_bounds",
  "timeout",
]);
export type ImageRejectReason = z.infer<typeof ImageRejectReasonSchema>;

export const ImageRejectedSchema = z.object({
  status: z.literal("image_rejected"),
  reason: ImageRejectReasonSchema,
}).strict();
export type ImageRejected = z.infer<typeof ImageRejectedSchema>;

// -----------------------------------------------------------------------------
// 2. No Food Detected
// -----------------------------------------------------------------------------
export const NoFoodDetectedSchema = z.object({
  status: z.literal("no_food_detected"),
}).strict();
export type NoFoodDetected = z.infer<typeof NoFoodDetectedSchema>;

// -----------------------------------------------------------------------------
// 3. Raw Food Detected
// -----------------------------------------------------------------------------
export const RawFoodDetectedSchema = z.object({
  status: z.literal("raw_food_detected"),
  food_name: z.string().max(255),
  suggested_quantity: z.string().max(100),
  candidates: z.array(z.string()).max(5),
}).strict();
export type RawFoodDetected = z.infer<typeof RawFoodDetectedSchema>;

// -----------------------------------------------------------------------------
// 4. Package Detected
// -----------------------------------------------------------------------------
export const PackageDetectedSchema = z.object({
  status: z.literal("package_detected"),
}).strict();
export type PackageDetected = z.infer<typeof PackageDetectedSchema>;

// -----------------------------------------------------------------------------
// 5. Label OCR Extracted
// -----------------------------------------------------------------------------
export const LabelOcrExtractedSchema = z.object({
  status: z.literal("label_ocr_extracted"),
  raw_text_snippet: z.string().max(1000).nullable(),
}).strict();
export type LabelOcrExtracted = z.infer<typeof LabelOcrExtractedSchema>;

// -----------------------------------------------------------------------------
// 6. OCR Validation Failed
// -----------------------------------------------------------------------------
export const OcrValidationFailedSchema = z.object({
  status: z.literal("ocr_validation_failed"),
  missing_fields: z.array(z.string()).max(20),
}).strict();
export type OcrValidationFailed = z.infer<typeof OcrValidationFailedSchema>;

// -----------------------------------------------------------------------------
// 7. Nutrition Result (with nested discriminated union for source)
// -----------------------------------------------------------------------------
export const UsdaSourceSchema = z.object({
  type: z.literal("usda"),
  fdc_id: z.string().max(50),
  usda_description: z.string().max(255),
}).strict();
export type UsdaSource = z.infer<typeof UsdaSourceSchema>;

export const LabelSourceSchema = z.object({
  type: z.literal("label"),
  ocr_confidence: z.number().min(0).max(1),
}).strict();
export type LabelSource = z.infer<typeof LabelSourceSchema>;

export const NutritionSourceSchema = z.discriminatedUnion("type", [
  UsdaSourceSchema,
  LabelSourceSchema,
]);
export type NutritionSource = z.infer<typeof NutritionSourceSchema>;

export const NutritionResultSchema = z.object({
  status: z.literal("nutrition_result"),
  food_name: z.string().max(255),
  serving_size: z.string().max(100).nullable(),
  calories: z.number().min(0).nullable(),
  protein_g: z.number().min(0).nullable(),
  carbs_g: z.number().min(0).nullable(),
  fat_g: z.number().min(0).nullable(),
  source: NutritionSourceSchema,
}).strict();
export type NutritionResult = z.infer<typeof NutritionResultSchema>;

// -----------------------------------------------------------------------------
// 8. Nutrition Not Found
// -----------------------------------------------------------------------------
export const NutritionNotFoundSchema = z.object({
  status: z.literal("nutrition_not_found"),
  item_name: z.string().max(100),
}).strict();
export type NutritionNotFound = z.infer<typeof NutritionNotFoundSchema>;

// -----------------------------------------------------------------------------
// 9. Error
// -----------------------------------------------------------------------------
export const ScanErrorSchema = z.object({
  status: z.literal("error"),
  message: z.string().max(500),
  retryable: z.boolean(),
}).strict();
export type ScanError = z.infer<typeof ScanErrorSchema>;

// =============================================================================
// MAIN EXPORT
// =============================================================================
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
