import type { ScanResponse } from "@/contracts/scan_contract";

interface ScanResultProps {
  data: ScanResponse;
}

export function ScanResult({ data }: ScanResultProps) {
  return (
    <div style={{ maxWidth: "600px", margin: "0 auto" }}>
      <h2>{data.food_name}</h2>
      <p>Type: {data.food_type} | Confidence: {(data.confidence * 100).toFixed(0)}%</p>

      {data.serving_size && <p>Serving Size: {data.serving_size}</p>}
      {data.calories != null && <p>Calories: {data.calories} kcal</p>}

      {data.nutrients.length > 0 && (
        <>
          <h3>Nutrients</h3>
          <ul>
            {data.nutrients.map((n, i) => (
              <li key={i}>
                {n.name}: {n.amount} {n.unit}
                {n.daily_value_percent != null && ` (${n.daily_value_percent}% DV)`}
              </li>
            ))}
          </ul>
        </>
      )}

      {data.ingredients.length > 0 && (
        <>
          <h3>Ingredients</h3>
          <p>{data.ingredients.join(", ")}</p>
        </>
      )}

      {data.warnings.length > 0 && (
        <div style={{ color: "orange", marginTop: "1rem" }}>
          <h3>⚠️ Warnings</h3>
          <ul>
            {data.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
