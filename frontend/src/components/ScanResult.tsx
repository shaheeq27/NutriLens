import type { ScanResponse } from "@/lib/api";

export type ScanResultProps = {
  response: Extract<ScanResponse, { status: "nutrition_result" }>;
};

const NUTRIENT_LABELS: Record<string, string> = {
  calories_kcal: "Calories",
  protein_g: "Protein",
  carbohydrates_g: "Carbohydrates",
  fat_g: "Fat",
  fiber_g: "Fiber",
  sugar_g: "Sugar",
  sodium_mg: "Sodium",
};

const NUTRIENT_UNITS: Record<string, string> = {
  calories_kcal: "kcal",
  protein_g: "g",
  carbohydrates_g: "g",
  fat_g: "g",
  fiber_g: "g",
  sugar_g: "g",
  sodium_mg: "mg",
};

export default function ScanResult({ response }: ScanResultProps) {
  const { source, food_name, quantity, serving_basis, nutrients } = response;
  const isDb = source.source === "database";

  return (
    <div className="space-y-4">
      <div className="w-full rounded-3xl border border-[#e8e8e3] bg-white p-5 soft-shadow">
      <div className="pb-3">
        <h2 className="text-lg font-bold text-[#18213a]">
          {food_name || "Packaged Product"}
        </h2>
        <h3 className="text-sm font-normal text-muted mt-1">
          {quantity ? `${quantity.amount} ${quantity.unit}` : (serving_basis || "Nutrition")}
        </h3>
      </div>

      <div className="label-rule" />

      <dl className="divide-y divide-[#edf0ec]">
        {Object.entries(nutrients).map(([key, value]) => {
          if (value === undefined || value === null) return null;
          return (
            <div
              key={key}
              className="flex items-baseline justify-between py-3"
            >
              <dt className="text-base text-[#435066]">
                {NUTRIENT_LABELS[key] ?? key}
              </dt>
              <dd className="font-mono text-base font-semibold tabular text-[#18213a]">
                {value}
                {NUTRIENT_UNITS[key] ? ` ${NUTRIENT_UNITS[key]}` : ""}
              </dd>
            </div>
          );
        })}
      </dl>

      <div className="label-rule" />

      <div className="pt-4">
        <span
          className={`inline-block rounded-full px-3 py-1 text-xs font-mono ${
            isDb ? "bg-database text-database-fg" : "bg-label text-label-fg"
          }`}
        >
          {source.source === "database" ? `${source.db_name}-sourced` : "Label-sourced"}
        </span>
      </div>
      </div>

      <section className={`rounded-3xl border px-6 py-5 ${response.health_insights.kind === "cautions" ? "border-[#ffd9d8] bg-[#fff1f0]" : "border-[#d5e8d9] bg-[#edf7ef]"}`}>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
          {response.health_insights.kind === "cautions" ? "Things to know" : "Why it can fit"}
        </p>
        <ul className="mt-3 space-y-3">
          {response.health_insights.items.map((item) => <li key={item} className="flex gap-3 text-sm leading-6 text-ink"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />{item}</li>)}
        </ul>
      </section>
    </div>
  );
}
