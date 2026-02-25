"use client";

import { useState, useRef } from "react";
import { uploadCourse } from "@/lib/api";
import { UploadResult } from "@/lib/types";

type Status = "idle" | "uploading" | "success" | "error";

export default function UploadForm({
  onSuccess,
}: {
  onSuccess?: (result: UploadResult) => void;
}) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState<UploadResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    setStatus("uploading");
    setError("");

    try {
      const res = await uploadCourse(file);
      setResult(res);
      setStatus("success");
      onSuccess?.(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("error");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          ref={fileRef}
          type="file"
          accept=".txt"
          required
          className="block text-sm file:mr-3 file:py-2 file:px-4 file:rounded file:border-0 file:bg-gray-800 file:text-white file:cursor-pointer hover:file:bg-gray-700"
        />
        <button
          type="submit"
          disabled={status === "uploading"}
          className="px-5 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
        >
          {status === "uploading" ? "Processing..." : "Process"}
        </button>
      </div>

      {status === "uploading" && (
        <p className="text-sm text-gray-400 animate-pulse">
          Running pipeline — this may take a moment...
        </p>
      )}

      {status === "success" && result && (
        <p className="text-sm text-green-400">
          {result.message} —{" "}
          <a
            href={`/courses/${result.course_slug}`}
            className="underline hover:text-green-300"
          >
            View course
          </a>
        </p>
      )}

      {status === "error" && (
        <p className="text-sm text-red-400">{error}</p>
      )}
    </form>
  );
}
