"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getCourse, jsonDownloadUrl, sqlDownloadUrl } from "@/lib/api";
import { CourseDetail } from "@/lib/types";
import ModuleAccordion from "@/components/ModuleAccordion";

export default function CourseDetailPage() {
  const params = useParams<{ slug: string }>();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getCourse(params.slug)
      .then(setCourse)
      .catch(() => setError("Course not found"));
  }, [params.slug]);

  if (error) {
    return (
      <div>
        <p className="text-red-400 mb-4">{error}</p>
        <Link href="/" className="text-blue-400 hover:underline text-sm">
          Back to home
        </Link>
      </div>
    );
  }

  if (!course) {
    return <p className="text-gray-400">Loading...</p>;
  }

  const totalChapters = course.modules.reduce(
    (sum, m) => sum + m.chapters.length,
    0
  );

  return (
    <div className="space-y-8">
      <div>
        <Link href="/" className="text-blue-400 hover:underline text-sm">
          &larr; Back
        </Link>
      </div>

      <div>
        <h1 className="text-2xl font-bold mb-1">{course.course_title}</h1>
        <p className="text-sm text-gray-400 mb-3">
          Slug: <code className="bg-gray-800 px-1.5 py-0.5 rounded">{course.course_slug}</code>
          {" "}&middot; {course.modules.length} modules &middot; {totalChapters} chapters
        </p>
        {course.course_description && (
          <p className="text-gray-300 text-sm leading-relaxed max-w-2xl">
            {course.course_description}
          </p>
        )}
      </div>

      {/* Download buttons */}
      <div className="flex gap-3">
        <a
          href={jsonDownloadUrl(params.slug)}
          download
          className="px-4 py-2 bg-green-700 text-white rounded text-sm hover:bg-green-600"
        >
          Download JSON
        </a>
        <a
          href={sqlDownloadUrl(params.slug)}
          download
          className="px-4 py-2 bg-purple-700 text-white rounded text-sm hover:bg-purple-600"
        >
          Download SQL
        </a>
      </div>

      {/* Modules */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Modules</h2>
        {course.modules.map((mod, i) => (
          <ModuleAccordion key={mod.slug} module={mod} index={i} />
        ))}
      </section>
    </div>
  );
}
