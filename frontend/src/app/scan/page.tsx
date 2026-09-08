"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import ImageUploader from "@/components/ImageUploader";
import ScanProgress, { type ScanStage } from "@/components/ScanProgress";
import ErrorState from "@/components/ErrorState";
import { submitScan, ScanApiError, type ScanResponse } from "@/lib/api";

const RESULT_STORAGE_KEY = "nutrilens:last-scan-response";

/**
 * PROVISIONAL: this page cannot complete an end-to-end scan yet — it
 * depends on Lane A's real contract (frontend/src/contracts/scan_contract.ts)
 * and Lane B's live /scan endpoint, neither of which exist in the repo yet.
 * The flow below is wired against the DRAFT §9 spec via lib/api.ts so the
 * UI shell is ready the moment both land.
 */
export default function ScanPage() {
  const router = useRouter();
  const [stage, setStage] = useState<ScanStage>("uploading");
  const [scanning, setScanning] = useState(false);
  const [errorResponse, setErrorResponse] = useState<
    Extract<
      ScanResponse,
      {
        status:
          | "image_rejected"
          | "no_food_detected"
          | "ocr_validation_failed"
          | "nutrition_not_found"
          | "error";
      }
    > | null
  >(null);

  const handleSelect = useCallback(
    async (file: File) => {
      setErrorResponse(null);
      setScanning(true);
      setStage("uploading");

      try {
        setStage("validating");
        const response = await submitScan(file);

        switch (response.status) {
          case "nutrition_result":
            sessionStorage.setItem(
              RESULT_STORAGE_KEY,
              JSON.stringify(response),
            );
            router.push("/result");
            return;
          case "raw_food_detected":
          case "package_detected":
          case "label_ocr_extracted":
            // These intermediate states need a follow-up interaction
            // (confirm quantity / take a label photo) that the backend
            // orchestrator and contract don't exist yet to drive. Once
            // Lane B's scan_orchestrator.py and Lane A's contract land,
            // this branch should route to the appropriate next step
            // instead of stopping here.
            setErrorResponse({
              status: "error",
              message:
                "This scan needs a follow-up step that isn't wired up yet.",
              retryable: true,
            });
            break;
          default:
            setErrorResponse(response);
        }
      } catch (err) {
        if (err instanceof ScanApiError) {
          setErrorResponse({
            status: "error",
            message: err.message,
            retryable: err.retryable,
          });
        } else {
          setErrorResponse({
            status: "error",
            message: "Something unexpected happened.",
            retryable: true,
          });
        }
      } finally {
        setScanning(false);
      }
    },
    [router],
  );

  const handleRetry = useCallback(() => {
    setErrorResponse(null);
  }, []);

  return (
    <main className="min-h-dvh flex flex-col gap-4 p-6">
      {scanning ? <ScanProgress stage={stage} /> : null}
      {errorResponse ? (
        <ErrorState response={errorResponse} onRetry={handleRetry} />
      ) : (
        <ImageUploader onSelect={handleSelect} disabled={scanning} />
      )}
    </main>
  );
}
