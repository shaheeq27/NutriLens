/**
 * API client for communicating with the NutriLens backend.
 */

import type { ScanResponse } from "@/contracts/scan_contract";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Upload a food image and receive nutritional analysis.
 */
export async function scanFood(file: File): Promise<ScanResponse> {
  const formData = new FormData();
  formData.append("image", file);

  const response = await fetch(`${API_URL}/api/scan`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail ?? `Scan failed with status ${response.status}`);
  }

  return response.json();
}
