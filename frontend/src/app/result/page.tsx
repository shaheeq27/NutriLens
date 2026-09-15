"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ScanResult from "@/components/ScanResult";
import type { ScanResponse } from "@/lib/api";

const RESULT_STORAGE_KEY = "nutrilens:last-scan-response";

export default function ResultPage() {
  const [result, setResult] = useState<Extract<ScanResponse, { status: "nutrition_result" }> | null | undefined>(undefined);
  useEffect(() => { const raw = sessionStorage.getItem(RESULT_STORAGE_KEY); if (!raw) return setResult(null); try { const parsed = JSON.parse(raw) as ScanResponse; setResult(parsed.status === "nutrition_result" ? parsed : null); } catch { setResult(null); } }, []);
  if (result === undefined) return null;
  if (result === null) return <main className="app-page flex min-h-dvh flex-col px-6 py-8"><Header /><section className="mt-32 rounded-3xl border border-[#e2e5df] bg-white p-7 text-center soft-shadow"><h1 className="text-2xl font-bold text-[#18213a]">No scan result yet</h1><p className="mt-3 text-sm leading-6 text-muted">Start with a clear photo of one food item.</p><Link href="/scan" className="mt-7 block rounded-full bg-[#1e4b33] py-4 text-sm font-semibold text-white">Start a scan</Link></section></main>;
  return <main className="app-page desktop-workspace min-h-dvh px-6 py-7 sm:px-8"><Header /><div className="mx-auto mt-10 max-w-xl"><FoodArt food={result.food_name || "Packaged Product"} /><div className="mt-7 text-center"><h1 className="text-3xl font-bold tracking-tight text-[#18213a]">{result.food_name || "Packaged Product"}</h1><p className="mt-2 text-sm text-muted">{result.source.source === "database" ? `Raw food · ${result.source.db_name}` : "Packaged food · From nutrition label"}</p></div><div className="mt-7"><ScanResult response={result} /></div><Link href="/scan" className="mt-6 block rounded-full border border-[#cfdacf] bg-white py-4 text-center text-sm font-semibold text-[#1e4b33]">Scan another item</Link></div></main>;
}

function Header() { return <header className="flex items-center justify-between"><Link href="/scan" className="text-4xl leading-none text-[#33445d]">‹</Link><span className="text-2xl font-bold tracking-[-0.07em] text-[#18213a]">Nutri<span className="text-[#6658eb]">Lens</span></span><span className="text-2xl text-[#33445d]">⇧</span></header>; }

function FoodArt({ food }: { food: string }) { const chocolate = /chocolate|bar|sweet/i.test(food); return <div className={`mx-auto grid h-48 w-64 place-items-center overflow-hidden rounded-3xl ${chocolate ? "bg-[#ead9c6]" : "bg-[#eaf3e6]"}`}><div className={chocolate ? "h-20 w-44 rotate-[-4deg] rounded-xl bg-[#4a281d] shadow-[inset_0_-12px_0_#2c1712]" : "relative h-28 w-28 rounded-[48%] bg-[radial-gradient(circle_at_35%_28%,#d5ef72_0_5%,transparent_6%),radial-gradient(circle_at_65%_40%,#8bc526_0_24%,#4c9228_60%,#2a652f_100%)] shadow-[0_24px_22px_rgba(30,75,51,.15)]"}><span className={!chocolate ? "absolute -top-5 left-1/2 h-7 w-2 -translate-x-1/2 rotate-[18deg] rounded-full bg-[#6b4f30]" : "hidden"} /></div></div>; }
