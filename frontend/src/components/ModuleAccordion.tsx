"use client";

import { useState } from "react";
import { Module } from "@/lib/types";

export default function ModuleAccordion({
  module,
  index,
}: {
  module: Module;
  index: number;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-5 py-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
      >
        <span className="font-medium">
          Module {index + 1}: {module.title}
        </span>
        <span className="text-gray-400 text-sm flex items-center gap-2">
          {module.chapters.length} chapter
          {module.chapters.length !== 1 && "s"}
          <svg
            className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </span>
      </button>

      {open && (
        <div className="border-t border-gray-700 divide-y divide-gray-800">
          {module.description && (
            <p className="px-5 py-3 text-sm text-gray-400">
              {module.description}
            </p>
          )}
          {module.chapters.map((ch, i) => (
            <div key={ch.slug} className="px-5 py-3">
              <p className="text-sm font-medium">
                Chapter {i + 1}: {ch.title}
              </p>
              {ch.description && (
                <p className="text-xs text-gray-400 mt-1">{ch.description}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
