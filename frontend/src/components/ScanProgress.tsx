export type ScanStage =
  | "uploading"
  | "validating"
  | "identifying"
  | "looking_up"
  | "done";

const STAGES: { key: ScanStage; label: string }[] = [
  { key: "uploading", label: "Uploading photo" },
  { key: "validating", label: "Checking image" },
  { key: "identifying", label: "Identifying food" },
  { key: "looking_up", label: "Looking up nutrition" },
  { key: "done", label: "Done" },
];

export type ScanProgressProps = {
  stage: ScanStage;
};

export default function ScanProgress({ stage }: ScanProgressProps) {
  const activeIndex = STAGES.findIndex((s) => s.key === stage);

  return (
    <div className="w-full bg-paper" role="status" aria-live="polite">
      <ol className="divide-y divide-ink border-y border-ink">
        {STAGES.map((s, i) => {
          const isDone = i < activeIndex;
          const isActive = i === activeIndex;
          return (
            <li
              key={s.key}
              className="flex items-center justify-between px-4 py-3"
            >
              <span
                className={`text-sm ${
                  isActive ? "text-ink font-medium" : isDone ? "text-muted" : "text-muted"
                }`}
              >
                {s.label}
              </span>
              <span className="font-mono text-xs tabular text-muted">
                {isDone ? "✓" : isActive ? "…" : ""}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
