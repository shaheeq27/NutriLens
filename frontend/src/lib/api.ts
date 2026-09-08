/**
 * PROVISIONAL — built against the frozen DRAFT spec in brief §9, because
 * `frontend/src/contracts/scan_contract.ts` (Lane A) does not exist in the
 * repo yet. Once Lane A lands the real contract file, replace the
 * `ScanResponse` type below with an import from "@/contracts/scan_contract"
 * and drop this local copy — do not maintain both.
 *
 * If Lane A's real field list differs from the §9 table, this file (and
 * the components that consume it) will need updating to match; that's
 * expected, not a bug.
 */

export type ScanResponse =
  | { status: "image_rejected"; reason: string }
  | { status: "no_food_detected" }
  | {
      status: "raw_food_detected";
      food_name: string;
      candidates?: string[];
      suggested_quantity: string;
    }
  | { status: "package_detected"; product_guess?: string }
  | { status: "label_ocr_extracted"; raw_fields: Record<string, string> }
  | {
      status: "ocr_validation_failed";
      reason: string;
      missing_fields?: string[];
    }
  | {
      status: "nutrition_result";
      source: "usda" | "label";
      food_name: string;
      quantity: string;
      nutrients: Record<string, number>;
    }
  | { status: "nutrition_not_found"; food_name: string }
  | { status: "error"; message: string; retryable: boolean };

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ScanApiError extends Error {
  constructor(
    message: string,
    public readonly retryable: boolean,
  ) {
    super(message);
    this.name = "ScanApiError";
  }
}

/**
 * Submits a captured/uploaded image to the backend scan endpoint.
 * The backend (Lane B, `backend/app/api/routes/scan.py`) doesn't exist yet
 * either — this will fail until both sides land. Client-side validation
 * still runs first (see ImageUploader) so obviously-bad files never reach
 * this call.
 */
export async function submitScan(image: File): Promise<ScanResponse> {
  const formData = new FormData();
  formData.append("image", image);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/scan`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new ScanApiError(
      "Couldn't reach the server. Check your connection and try again.",
      true,
    );
  }

  if (!response.ok) {
    throw new ScanApiError(
      `Scan request failed (${response.status}).`,
      response.status >= 500,
    );
  }

  const data = (await response.json()) as ScanResponse;
  return data;
}
