/**
 * Shared contracts (schemas) for the scan feature.
 * Mirrors backend/app/contracts/scan_contract.py
 */

export type FoodType = "raw" | "packaged" | "unknown";

export interface NutrientInfo {
  name: string;
  amount: number;
  unit: string;
  daily_value_percent: number | null;
}

export interface ScanResponse {
  food_name: string;
  food_type: FoodType;
  serving_size: string | null;
  calories: number | null;
  nutrients: NutrientInfo[];
  ingredients: string[];
  confidence: number;
  warnings: string[];
}
