import { ScanResponse, ScanResponseSchema } from "@/contracts/scan_contract";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
 */
export async function submitScan(file: File): Promise<ScanResponse> {
  const formData = new FormData();
  formData.append("file", file);

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

  const json = await response.json();
  const result = ScanResponseSchema.safeParse(json);

  if (!result.success) {
    throw new ScanApiError("Received malformed response from the server.", false);
  }

  return result.data;
}

export async function confirmRawFood(foodName: string, portionGrams: number): Promise<ScanResponse> {
  const formData = new FormData();
  formData.append("food_name", foodName);
  formData.append("portion_grams", String(portionGrams));
  return request("/scan/raw-food", formData);
}

export async function validateLabel(rawFields: Record<string, string>, servingBasis?: string | null, productGuess?: string | null): Promise<ScanResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/scan/label/validate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ raw_fields: rawFields, serving_basis: servingBasis, product_guess: productGuess }) });
  } catch {
    throw new ScanApiError("Couldn’t reach NutriLens. Is the API running?", true);
  }
  const json = await response.json().catch(() => null);
  if (!response.ok) throw new ScanApiError(`The scan failed (${response.status}).`, response.status >= 500);
  const parsed = ScanResponseSchema.safeParse(json);
  if (!parsed.success) throw new ScanApiError("The server returned an invalid scan result.", false);
  return parsed.data;
}

export async function submitLabel(file: File): Promise<ScanResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request("/scan/label", formData);
}

async function request(path: string, body: FormData): Promise<ScanResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", body });
  } catch {
    throw new ScanApiError("Couldn’t reach NutriLens. Is the API running?", true);
  }
  const json = await response.json().catch(() => null);
  if (!response.ok) throw new ScanApiError(`The scan failed (${response.status}).`, response.status >= 500);
  const parsed = ScanResponseSchema.safeParse(json);
  if (!parsed.success) throw new ScanApiError("The server returned an invalid scan result.", false);
  return parsed.data;
}

export type { ScanResponse };
