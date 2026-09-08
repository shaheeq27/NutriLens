"use client";

import { useCallback, useRef, useState } from "react";

const MAX_FILE_BYTES = 12 * 1024 * 1024; // 12MB — mirrors backend size cap
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export type ImageUploaderProps = {
  onSelect: (file: File) => void;
  disabled?: boolean;
};

type LocalValidationError = { message: string };

/**
 * Client-side validation here is a UX convenience only — a fast, friendly
 * rejection before upload. It does NOT replace the backend's own
 * validation (size, type, magic bytes, dimensions, megapixel limit, decode
 * timeout — §3, §5), which remains the source of truth and runs
 * regardless of what this component allows through.
 */
function validateLocally(file: File): LocalValidationError | null {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return { message: "Please choose a JPEG, PNG, or WebP photo." };
  }
  if (file.size > MAX_FILE_BYTES) {
    return { message: "That photo is too large — try one under 12MB." };
  }
  return null;
}

export default function ImageUploader({ onSelect, disabled }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      const validationError = validateLocally(file);
      if (validationError) {
        setError(validationError.message);
        return;
      }
      setError(null);
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return URL.createObjectURL(file);
      });
      onSelect(file);
    },
    [onSelect],
  );

  return (
    <div className="label-frame w-full bg-paper p-6">
      <p className="text-xs uppercase tracking-wide text-muted mb-4">
        Scan a food item
      </p>

      {previewUrl ? (
        <div className="mb-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="Selected food photo preview"
            className="w-full object-cover"
            style={{ maxHeight: "320px" }}
          />
        </div>
      ) : null}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        disabled={disabled}
        className="sr-only"
        id="food-photo-input"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      <label
        htmlFor="food-photo-input"
        className={`block w-full text-center py-4 border border-ink cursor-pointer ${
          disabled ? "opacity-50 pointer-events-none" : ""
        }`}
      >
        {previewUrl ? "Choose a different photo" : "Take or choose a photo"}
      </label>

      {error ? (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      ) : (
        <p className="mt-3 text-sm text-muted">
          One item at a time works best — a single fruit, a package, a plate
          with one food on it.
        </p>
      )}
    </div>
  );
}
