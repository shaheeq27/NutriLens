import type { ScanResponse } from "@/lib/api";

export type ScanResultProps = {
  response: Extract<ScanResponse, { status: "nutrition_result" }>;
};

const NUTRIENT_LABELS: Record<string, string> = {
  calories: "Calories",
  protein: "Protein",
  carbs: "Carbohydrates",
  fat: "Fat",
};

const NUTRIENT_UNITS: Record<string, string> = {
  calories: "kcal",
  protein: "g",
  carbs: "g",
  fat: "g",
};

export default function ScanResult({ response }: ScanResultProps) {
  const { source, food_name, quantity, nutrients } = response;
  const isUsda = source === "usda";

  return (
    <div className="label-frame w-full bg-paper">
      <div className="px-6 pt-6 pb-4">
        <p className="text-xs uppercase tracking-wide text-muted mb-1">
          {isUsda ? "Raw food · USDA FoodData Central" : "Packaged food · from the printed label"}
        </p>
        <h2 className="text-2xl font-medium text-ink">{food_name}</h2>
        <p className="text-sm text-muted mt-1">{quantity}</p>
      </div>

      <div className="label-rule" />

      <dl className="divide-y divide-ink/20">
        {Object.entries(nutrients).map(([key, value]) => (
          <div
            key={key}
            className="flex items-baseline justify-between px-6 py-3"
          >
            <dt className="text-sm text-ink">
              {NUTRIENT_LABELS[key] ?? key}
            </dt>
            <dd className="font-mono text-sm tabular text-ink">
              {value}
              {NUTRIENT_UNITS[key] ? ` ${NUTRIENT_UNITS[key]}` : ""}
            </dd>
          </div>
        ))}
      </dl>

      <div className="label-rule" />

      <div className="px-6 py-4">
        <span
          className={`inline-block px-2 py-1 text-xs font-mono ${
            isUsda ? "bg-usda text-usda-fg" : "bg-label text-label-fg"
          }`}
        >
          {isUsda ? "USDA-sourced" : "Label-sourced"}
        </span>
      </div>
    </div>
  );
}
