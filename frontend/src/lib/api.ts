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

export type { ScanResponse };
