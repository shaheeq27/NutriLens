"use client";
/* eslint-disable @next/next/no-img-element */

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ImageUploader from "@/components/ImageUploader";
import ScanProgress, { type ScanStage } from "@/components/ScanProgress";
import ErrorState from "@/components/ErrorState";
import { confirmRawFood, submitLabel, validateLabel, submitScan, ScanApiError, type ScanResponse } from "@/lib/api";

const RESULT_STORAGE_KEY = "nutrilens:last-scan-response";
type ErrorResponse = Extract<ScanResponse, { status: "image_rejected" | "no_food_detected" | "ocr_validation_failed" | "nutrition_not_found" | "error" }>;
type View = "choose" | "camera" | "preview" | "working" | "flow";

export default function ScanPage() {
  const router = useRouter();
  const cameraRef = useRef<HTMLInputElement>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  const [view, setView] = useState<View>("choose");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [stage, setStage] = useState<ScanStage>("uploading");
  const [rawFood, setRawFood] = useState<Extract<ScanResponse, { status: "raw_food_detected" }> | null>(null);
  const [packaged, setPackaged] = useState(false);
  const [productGuess, setProductGuess] = useState<string | null>(null);
  const [labelFields, setLabelFields] = useState<Extract<ScanResponse, { status: "label_ocr_extracted" }> | null>(null);
  const [errorResponse, setErrorResponse] = useState<ErrorResponse | null>(null);

  const reset = () => { setView("choose"); setSelectedFile(null); setPreviewUrl(null); setRawFood(null); setPackaged(false); setProductGuess(null); setLabelFields(null); setErrorResponse(null); };
  const chooseFile = (file: File | undefined) => { if (!file) return; setSelectedFile(file); setPreviewUrl(URL.createObjectURL(file)); setView("preview"); };
  const storeResult = (response: Extract<ScanResponse, { status: "nutrition_result" }>) => { sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(response)); router.push("/result"); };
  const handleResponse = (response: ScanResponse) => {
    if (response.status === "nutrition_result") return storeResult(response);
    if (response.status === "raw_food_detected") { setRawFood(response); setPackaged(false); setView("flow"); return; }
    if (response.status === "package_detected") { setPackaged(true); setProductGuess(response.product_guess || null); setRawFood(null); setView("flow"); return; }
    if (response.status === "label_ocr_extracted") { setLabelFields(response); setPackaged(false); setView("flow"); return; }
    setErrorResponse(response as ErrorResponse); setView("flow");
  };
  const analyze = async (file: File) => {
    setView("working"); setErrorResponse(null); setStage("validating");
    try { setStage("identifying"); await new Promise((resolve) => setTimeout(resolve, 550)); handleResponse(await submitScan(file)); }
    catch (err) { setErrorResponse({ status: "error", message: err instanceof ScanApiError ? err.message : "Something unexpected happened.", retryable: true }); setView("flow"); }
  };
  const confirm = async (portion: number) => { if (!rawFood) return; setView("working"); setStage("looking_up"); try { handleResponse(await confirmRawFood(rawFood.food_name, portion)); } catch (err) { setErrorResponse({ status: "error", message: err instanceof ScanApiError ? err.message : "Nutrition lookup failed.", retryable: true }); setView("flow"); } };
  const label = async (file: File) => { setView("working"); setStage("looking_up"); try { handleResponse(await submitLabel(file)); } catch (err) { setErrorResponse({ status: "error", message: err instanceof ScanApiError ? err.message : "Label reading failed.", retryable: true }); setView("flow"); } };
  const completeLabel = async () => {
    if (!labelFields) return;
    setView("working");
    setStage("looking_up");
    try {
      handleResponse(await validateLabel(labelFields.raw_fields, labelFields.serving_basis, productGuess));
    } catch (err) {
      setErrorResponse({ status: "error", message: err instanceof ScanApiError ? err.message : "Validation failed.", retryable: true });
      setView("flow");
    }
  };

  if (view === "camera") return <CameraView onCancel={() => setView("choose")} onCapture={() => cameraRef.current?.click()} input={<input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => chooseFile(e.target.files?.[0])} />} />;
  if (view === "preview" && selectedFile && previewUrl) return <PreviewView src={previewUrl} onRetake={reset} onAnalyze={() => analyze(selectedFile)} />;
  if (view === "working") return <WorkingView stage={stage} />;

  return <main className="app-page desktop-workspace mx-auto flex min-h-dvh w-full max-w-xl flex-col px-6 py-7 sm:px-8">
    <Header />
    {view === "choose" ? <ChooseSource onCamera={() => setView("camera")} onUpload={() => uploadRef.current?.click()} input={<input ref={uploadRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => chooseFile(e.target.files?.[0])} />} /> : null}
    {errorResponse ? <ErrorState response={errorResponse} onRetry={reset} /> : null}
    {rawFood && !errorResponse ? <QuantityCard food={rawFood} onConfirm={confirm} onReset={reset} /> : null}
    {packaged && !errorResponse ? <section className="mt-8 rounded-3xl border border-[#e2e5df] bg-white p-6 soft-shadow"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Packaged food detected</p><h2 className="mt-3 text-2xl font-bold tracking-tight text-ink">Photograph the nutrition panel.</h2><p className="mt-2 text-sm leading-6 text-muted">Use a straight-on, well-lit photo where the full label is visible.</p><div className="mt-6"><ImageUploader label="Upload nutrition label" helpText="JPEG, PNG, or WebP · one label at a time" onSelect={label} /></div></section> : null}
    {labelFields && !errorResponse ? <LabelReadout fields={labelFields.raw_fields} onReset={reset} onComplete={completeLabel} /> : null}
    {view === "choose" && !errorResponse ? <div className="mt-auto rounded-2xl border border-[#e2e8f0] bg-[#f3f7fb] px-5 py-4 text-sm text-[#51627d]"><span className="mr-3 text-[#6658eb]">✦</span>Works for fruits, vegetables, packaged foods, and more.</div> : null}
  </main>;
}

function Header() { return <header className="flex items-center justify-between"><div className="flex items-center gap-2"><span className="text-2xl font-bold tracking-[-0.07em] text-[#1e4b33]">Nutri<span className="text-[#6658eb]">Lens</span></span></div><span className="text-sm text-[#687897]">See food. Know better.</span></header>; }

function ChooseSource({ onCamera, onUpload, input }: { onCamera: () => void; onUpload: () => void; input: React.ReactNode }) { return <section className="flex flex-1 flex-col pt-16 text-center"><h1 className="text-4xl font-bold leading-[1.08] tracking-[-0.06em] text-[#111a31]">What’s on<br />your plate today?</h1><p className="mx-auto mt-5 max-w-sm text-base leading-7 text-[#687897]">Take a photo or upload an image to analyze its nutrition and get simple insights.</p><div className="mt-10 grid grid-cols-2 gap-4 text-left"><button type="button" onClick={onCamera} className="min-h-56 rounded-3xl border border-[#eef1f6] bg-white p-6 text-center soft-shadow transition hover:-translate-y-1"><IconBox tone="violet"><CameraIcon /></IconBox><strong className="mt-5 block text-base text-[#18213a]">Take a Photo</strong><span className="mt-2 block text-sm text-[#8a9ab8]">Use your camera</span></button><button type="button" onClick={onUpload} className="min-h-56 rounded-3xl border border-[#eef1f6] bg-white p-6 text-center soft-shadow transition hover:-translate-y-1"><IconBox tone="coral"><ImageIcon /></IconBox><strong className="mt-5 block text-base text-[#18213a]">Upload Image</strong><span className="mt-2 block text-sm text-[#8a9ab8]">Choose from device</span></button></div>{input}</section>; }
function IconBox({ tone, children }: { tone: "violet" | "coral"; children: React.ReactNode }) { return <span className={`mx-auto grid h-16 w-16 place-items-center rounded-2xl ${tone === "violet" ? "bg-[#eef0ff] text-[#6658eb]" : "bg-[#fff0ec] text-[#eb725e]"}`}>{children}</span>; }
function CameraIcon() { return <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 8h3l1.5-2h7L17 8h3v10H4Z" /><circle cx="12" cy="13" r="3" /></svg>; }
function ImageIcon() { return <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="4" y="5" width="16" height="14" rx="2" /><circle cx="9" cy="10" r="1" /><path d="m5 17 4-4 3 3 2-2 5 4" /></svg>; }

function CameraView({ onCancel, onCapture, input }: { onCancel: () => void; onCapture: () => void; input: React.ReactNode }) { return <main className="camera-stage flex flex-col items-center px-6 py-8"><div className="flex w-full max-w-md items-center justify-between text-lg"><button type="button" onClick={onCancel}>Cancel</button><span className="text-2xl">ϟ</span></div><div className="mt-36 camera-window"><span className="absolute inset-1/2 h-px w-5 -translate-x-1/2 bg-white/70" /><span className="absolute inset-1/2 h-5 w-px -translate-y-1/2 bg-white/70" /></div><p className="mt-8 text-base text-white/70">Tap to capture</p><button type="button" onClick={onCapture} className="mt-auto grid h-24 w-24 place-items-center rounded-full border-4 border-white bg-transparent p-2"><span className="h-full w-full rounded-full border-2 border-white" /></button>{input}</main>; }
function PreviewView({ src, onRetake, onAnalyze }: { src: string; onRetake: () => void; onAnalyze: () => void }) { return <main className="app-page flex min-h-dvh flex-col px-6 py-8"><button type="button" onClick={onRetake} className="w-fit text-4xl leading-none text-[#33445d]">‹</button><div className="mx-auto mt-24 w-full max-w-md overflow-hidden rounded-3xl">{/* eslint-disable-next-line @next/next/no-img-element */}<img src={src} alt="Selected food" className="aspect-square w-full object-cover" /></div><h1 className="mt-8 text-center text-3xl font-bold tracking-tight text-[#111a31]">Looks good?</h1><p className="mt-3 text-center text-base text-[#687897]">Make sure the food is clear and well lit.</p><div className="mt-auto grid grid-cols-2 gap-5"><button type="button" onClick={onRetake} className="min-h-16 rounded-full border border-[#cbd9e6] bg-white text-base font-semibold text-[#202a3c]">Retake</button><button type="button" onClick={onAnalyze} className="min-h-16 rounded-full bg-[#1e4b33] text-base font-semibold text-white lift-shadow">Analyze</button></div></main>; }
function WorkingView({ stage }: { stage: ScanStage }) { const active = stage === "looking_up" ? 2 : 1; const labels = ["Processing image...", "Identifying food item...", "Fetching nutrition data...", "Generating insights..."]; return <main className="app-page flex min-h-dvh flex-col px-6 py-8"><Header /><section className="flex flex-1 flex-col items-center pt-14 text-center"><h1 className="text-3xl font-bold tracking-tight text-[#111a31]">Analyzing your food...</h1><p className="mt-3 max-w-sm text-base leading-7 text-[#687897]">Identifying the food item and retrieving nutrition information.</p><div className="relative mt-14"><div className="scan-orbit" /><span className="absolute inset-0 grid place-items-center text-4xl text-[#35644a]">ψ</span></div><ol className="mt-12 w-full max-w-sm space-y-5 text-left">{labels.map((label, i) => <li key={label} className="flex items-center gap-4 text-sm text-[#52627b]"><span className={i <= active ? "state-check" : "state-pending"}>{i <= active ? "✓" : ""}</span><span className={i === active + 1 ? "font-semibold text-[#18213a]" : ""}>{label}</span></li>)}</ol><div className="mt-auto w-full max-w-md rounded-2xl border border-[#f4d9bd] bg-[#fff5e9] px-5 py-4 text-sm text-[#8c5b2a]">✦ &nbsp; This usually takes a few seconds.</div></section></main>; }
function QuantityCard({ food, onConfirm, onReset }: { food: Extract<ScanResponse, { status: "raw_food_detected" }>; onConfirm: (portion: number) => void; onReset: () => void }) { const [portion, setPortion] = useState(food.suggested_quantity ? String(food.suggested_quantity.amount) : "100"); return <section className="mt-8 rounded-3xl border border-[#e2e5df] bg-white p-6 soft-shadow"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1e4b33]">Food identified</p><h2 className="mt-3 text-3xl font-bold tracking-tight text-[#18213a]">{food.food_name}</h2><p className="mt-2 text-sm leading-6 text-muted">Confirm the amount so the nutrition values match what you actually eat.</p><label className="mt-6 block text-sm font-medium text-[#18213a]" htmlFor="portion">Portion in grams</label><div className="mt-2 flex gap-3"><input id="portion" type="number" min="1" value={portion} onChange={(e) => setPortion(e.target.value)} className="min-w-0 flex-1 rounded-xl border border-[#dce3dc] px-4 py-3 text-lg" /><button type="button" onClick={() => onConfirm(Number(portion))} className="rounded-xl bg-[#1e4b33] px-4 py-3 text-sm font-semibold text-white">Analyze</button></div><button type="button" onClick={onReset} className="mt-4 text-sm text-muted underline">Choose another image</button></section>; }
function LabelReadout({ fields, onReset, onComplete }: { fields: Record<string, string>; onReset: () => void; onComplete: () => void }) { const labels: Record<string, string> = { energy_kcal: "Calories", protein_g: "Protein", carbohydrates_g: "Carbohydrates", fat_g: "Fat", fiber_g: "Fiber", sugar_g: "Sugar", sodium_mg: "Sodium" }; return <section className="mt-8 rounded-3xl border border-[#e2e5df] bg-white p-6 soft-shadow"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#1e4b33]">Label read successfully</p><h2 className="mt-3 text-2xl font-bold text-[#18213a]">Nutrition facts found</h2><p className="mt-2 text-sm leading-6 text-muted">These values were transcribed from the photographed nutrition panel.</p><dl className="mt-6 divide-y divide-[#edf0ec] border-y border-[#dfe7df]">{Object.entries(fields).map(([key, value]) => <div key={key} className="flex justify-between py-3 text-sm"><dt>{labels[key] ?? key}</dt><dd className="font-mono">{value}</dd></div>)}</dl><button type="button" onClick={onComplete} className="mt-6 w-full rounded-full bg-[#1e4b33] py-4 text-sm font-semibold text-white">View nutrition</button><button type="button" onClick={onReset} className="mt-4 text-sm text-muted underline">Scan another item</button></section>; }
