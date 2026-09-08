import Link from "next/link";

export default function HomePage() {
  return (
    <main style={{ padding: "2rem", textAlign: "center" }}>
      <h1>🍎 NutriLens</h1>
      <p>AI-powered food nutrition scanner</p>
      <p>Snap a photo of raw food or a packaged food label to get instant nutritional insights.</p>
      <Link href="/scan" style={{ fontSize: "1.2rem", marginTop: "1rem", display: "inline-block" }}>
        Start Scanning →
      </Link>
    </main>
  );
}
