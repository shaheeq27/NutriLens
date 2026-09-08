import type { NextConfig } from "next";

/**
 * NutriLens frontend config.
 *
 * Kept deliberately minimal for V1: no remote image domains are configured
 * because scanned photos are handled client-side / in-memory only and are
 * never persisted or served back from a CDN (see brief §3, §5 — no
 * permanent photo storage).
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
