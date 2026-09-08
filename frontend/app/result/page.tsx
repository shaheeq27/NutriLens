"use client";

import { ScanResult } from "@/components/ScanResult";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { ScanResponse } from "@/contracts/scan_contract";

export default function ResultPage() {
  const [result, setResult] = useState<ScanResponse | null>(null);
  const router = useRouter();

  useEffect(() => {
    const stored = sessionStorage.getItem("scanResult");
    if (stored) {
      setResult(JSON.parse(stored));
    } else {
      router.push("/scan");
    }
  }, [router]);

  if (!result) {
    return <p style={{ textAlign: "center", padding: "2rem" }}>Loading...</p>;
  }

  return (
    <main style={{ padding: "2rem" }}>
      <ScanResult data={result} />
      <div style={{ textAlign: "center", marginTop: "1rem" }}>
        <button onClick={() => router.push("/scan")}>Scan Another</button>
      </div>
    </main>
  );
}
