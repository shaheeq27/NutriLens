"use client";

import { ImageUploader } from "@/components/ImageUploader";
import { ScanProgress } from "@/components/ScanProgress";
import { ErrorState } from "@/components/ErrorState";
import { scanFood } from "@/lib/api";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function ScanPage() {
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleUpload = async (file: File) => {
    setIsScanning(true);
    setError(null);

    try {
      const result = await scanFood(file);
      // Store result and navigate
      sessionStorage.setItem("scanResult", JSON.stringify(result));
      router.push("/result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed. Please try again.");
    } finally {
      setIsScanning(false);
    }
  };

  if (error) {
    return <ErrorState message={error} onRetry={() => setError(null)} />;
  }

  if (isScanning) {
    return <ScanProgress />;
  }

  return (
    <main style={{ padding: "2rem", textAlign: "center" }}>
      <h1>📷 Scan Food</h1>
      <p>Upload a photo of raw food or a packaged food label.</p>
      <ImageUploader onUpload={handleUpload} />
    </main>
  );
}
