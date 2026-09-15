"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ScanResult from "@/components/ScanResult";
import type { ScanResponse } from "@/lib/api";

const RESULT_STORAGE_KEY = "nutrilens:last-scan-response";

export default function ResultPage() {
  const [result, setResult] = useState<Extract<ScanResponse, { status: "nutrition_result" }> | null | undefined>(undefined);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem(RESULT_STORAGE_KEY);
    const img = sessionStorage.getItem("nutrilens:image");
    if (img) setImageUrl(img);

    if (!raw) return setResult(null);
    try {
      const parsed = JSON.parse(raw) as ScanResponse;
      setResult(parsed.status === "nutrition_result" ? parsed : null);
    } catch {
      setResult(null);
    }
  }, []);

  if (result === undefined) return null;
  if (result === null) return <main className="app-page flex min-h-dvh flex-col px-6 py-8"><Header /><section className="mt-32 rounded-3xl border border-[#e2e5df] bg-white p-7 text-center soft-shadow"><h1 className="text-2xl font-bold text-[#18213a]">No scan result yet</h1><p className="mt-3 text-sm leading-6 text-muted">Start with a clear photo of one food item.</p><Link href="/scan" className="mt-7 block rounded-full bg-[#1e4b33] py-4 text-sm font-semibold text-white">Start a scan</Link></section></main>;
  return <main className="app-page desktop-workspace min-h-dvh px-6 py-7 sm:px-8"><Header /><div className="mx-auto mt-10 max-w-xl"><FoodPhoto src={imageUrl} /><div className="mt-7 text-center"><h1 className="text-3xl font-bold tracking-tight text-[#18213a]">{result.food_name || "Packaged Product"}</h1><p className="mt-2 text-sm text-muted">{result.source.source === "database" ? `Raw food · ${result.source.db_name}` : "Packaged food · From nutrition label"}</p></div><div className="mt-7"><ScanResult response={result} /></div><Link href="/scan" className="mt-6 block rounded-full border border-[#cfdacf] bg-white py-4 text-center text-sm font-semibold text-[#1e4b33]">Scan another item</Link></div></main>;
}

function Header() { return <header className="flex items-center justify-between"><Link href="/scan" className="text-4xl leading-none text-[#33445d]">‹</Link><span className="text-2xl font-bold tracking-[-0.07em] text-[#18213a]">Nutri<span className="text-[#6658eb]">Lens</span></span><span className="text-2xl text-[#33445d]">⇧</span></header>; }

function FoodPhoto({ src }: { src: string | null }) {
  return <div className="mx-auto grid h-48 w-64 place-items-center overflow-hidden rounded-3xl bg-[#eef1f6]">
    {src ? (
      /* eslint-disable-next-line @next/next/no-img-element */
      <img src={src} alt="Analyzed food" className="h-full w-full object-cover" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
    ) : (
      <span className="text-3xl text-[#a0afc0]">🍽️</span>
    )}
  </div>;
}
