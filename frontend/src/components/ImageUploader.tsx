"use client";

import { useRef } from "react";

interface ImageUploaderProps {
  onUpload: (file: File) => void;
}

export function ImageUploader({ onUpload }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
    }
  };

  return (
    <div style={{ marginTop: "2rem" }}>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleChange}
        style={{ display: "none" }}
      />
      <button
        onClick={() => inputRef.current?.click()}
        style={{ padding: "1rem 2rem", fontSize: "1rem", cursor: "pointer" }}
      >
        📷 Upload Photo
      </button>
    </div>
  );
}
