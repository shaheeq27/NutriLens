import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        paper: "#faf7ef",
        ink: "#211f1a",
        muted: "#706d64",
        primary: "#2b5e42",
        line: "#d9d4c7",
        danger: "#a23b2a",
        database: "#e6f0e7",
        "database-fg": "#235331",
        label: "#f4ead5",
        "label-fg": "#7b5614",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
