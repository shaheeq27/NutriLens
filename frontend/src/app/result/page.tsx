"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ScanResult from "@/components/ScanResult";
import type { ScanResponse } from "@/lib/api";

const RESULT_STORAGE_KEY = "nutrilens:last-scan-response";

export default function ResultPage() {
  const [result, setResult] = useState<
    Extract<ScanResponse, { status: "nutrition_result" }> | null | undefined
  >(undefined);

  useEffect(() => {
    const raw = sessionStorage.getItem(RESULT_STORAGE_KEY);
    if (!raw) {
      setResult(null);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as ScanResponse;
      setResult(parsed.status === "nutrition_result" ? parsed : null);
    } catch {
      setResult(null);
    }
  }, []);

  if (result === undefined) {
    return null;
  }

  if (result === null) {
    return (
      <main className="min-h-dvh flex flex-col gap-4 p-6">
        <div className="label-frame bg-paper p-6">
          <p className="text-sm text-muted mb-4">
            No scan result to show. Start a new scan to see one.
          </p>
          <Link
            href="/scan"
            className="block w-full text-center py-3 border border-ink text-sm"
          >
            Start a scan
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-dvh flex flex-col gap-4 p-6">
      <ScanResult response={result} />
      <Link
        href="/scan"
        className="block w-full text-center py-3 border border-ink text-sm"
      >
        Scan another item
      </Link>
    </main>
  );
}
