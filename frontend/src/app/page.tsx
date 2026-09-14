import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <main className="app-page desktop-workspace flex flex-col px-6 py-8 sm:px-10">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3"><span className="brand-mark">◎</span><span className="text-xl font-bold tracking-tight text-[#1e4b33]">NutriLens</span></div>
        <span className="hidden text-sm text-muted sm:block">See food. Know better.</span>
      </header>
      <section className="flex flex-1 flex-col items-center pt-16 text-center sm:pt-24">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#1e4b33]">A clearer relationship with food</p>
        <h1 className="mt-5 max-w-xl text-5xl font-bold leading-[0.98] tracking-[-0.06em] text-[#292f2b] sm:text-7xl">Real Food.<br /><span className="text-[#1e4b33]">Real Insights.</span></h1>
        <p className="mt-6 max-w-md text-base leading-7 text-muted sm:text-lg">Upload or scan a food image to get nutrition facts and simple, useful health insights.</p>
        <Link href="/scan" className="mt-8 flex min-h-16 w-full max-w-sm items-center justify-center rounded-full bg-[#1e4b33] text-lg font-semibold text-white transition hover:-translate-y-0.5">Scan Food Now</Link>
        <div className="relative mt-16 flex items-center gap-3 sm:mt-20"><span className="absolute -left-16 top-8 w-24 -rotate-6 text-left font-serif text-2xl italic leading-tight text-[#35644a]">Good food,<br />brighter<br />days.</span><Image className="hero-bowl" src="/food-bowl-cutout.png" alt="Colorful bowl of real food" width={320} height={320} priority /><span className="absolute -right-4 bottom-4 grid h-10 w-10 place-items-center rounded-full border border-[#b9c9bb] bg-[#e8f0e5] text-[#1e4b33]">⌁</span></div>
        <div className="mt-14 grid w-full max-w-md grid-cols-4 gap-2 rounded-3xl border border-white bg-white/85 px-4 py-5 soft-shadow"><Category label="Fruits" tone="green" /><Category label="Vegetables" tone="orange" /><Category label="Packaged Foods" tone="sand" /><Category label="Meals & More" tone="blue" /></div>
      </section>
    </main>
  );
}

function Category({ label, tone }: { label: string; tone: "green" | "orange" | "sand" | "blue" }) {
  const colors = { green: "#e7f2e9", orange: "#faeee2", sand: "#f2ece3", blue: "#edf1f7" };
  return <div className="flex flex-col items-center gap-2 text-center text-xs font-medium text-[#424942]"><span className="grid h-10 w-10 place-items-center rounded-full" style={{ background: colors[tone] }}><span className="h-3 w-3 rounded-full bg-[#1e4b33] opacity-75" /></span><span>{label}</span></div>;
}
