"use client";

import type { ScanResponse } from "@/lib/api";

export type ErrorStateProps = {
  response: Extract<
    ScanResponse,
    {
      status:
        | "image_rejected"
        | "no_food_detected"
        | "ocr_validation_failed"
        | "nutrition_not_found"
        | "error";
    }
  >;
  onRetry: () => void;
};

function messageFor(response: ErrorStateProps["response"]): {
  heading: string;
  detail: string;
  canRetry: boolean;
} {
  switch (response.status) {
    case "image_rejected":
      return {
        heading: "That photo didn't work",
        detail: `Reason: ${response.reason}. Try a clear, well-lit photo with the food filling most of the frame.`,
        canRetry: true,
      };
    case "no_food_detected":
      return {
        heading: "No food found in that photo",
        detail: "Point the camera directly at the item and try again.",
        canRetry: true,
      };
    case "ocr_validation_failed":
      return {
        heading: "Couldn't read the label",
        detail: response.missing_fields?.length
          ? `Missing or unclear: ${response.missing_fields.join(", ")}. Try a straight-on, well-lit photo of the nutrition panel.`
          : "Try a straight-on, well-lit photo of the nutrition panel.",
        canRetry: true,
      };
    case "nutrition_not_found":
      return {
        heading: `No nutrition match for "${response.food_name}"`,
        detail:
          "NutriLens doesn't estimate nutrition values, so it won't guess here. Try a more specific or common name for this food.",
        canRetry: true,
      };
    case "error":
      return {
        heading: "Something went wrong",
        detail: response.message,
        canRetry: response.retryable,
      };
  }
}

export default function ErrorState({ response, onRetry }: ErrorStateProps) {
  const { heading, detail, canRetry } = messageFor(response);

  return (
    <div className="label-frame w-full bg-paper p-6">
      <p className="text-xs uppercase tracking-wide text-danger mb-2">
        Scan stopped
      </p>
      <h2 className="text-lg font-medium text-ink mb-2">{heading}</h2>
      <p className="text-sm text-muted mb-6">{detail}</p>
      {canRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="w-full py-3 border border-ink text-sm"
        >
          Try another photo
        </button>
      ) : null}
    </div>
  );
}
