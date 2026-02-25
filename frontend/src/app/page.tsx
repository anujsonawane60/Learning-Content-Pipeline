"use client";

import { useEffect, useState, useCallback } from "react";
import { listCourses } from "@/lib/api";
import { CourseListItem } from "@/lib/types";
import UploadForm from "@/components/UploadForm";
import CourseCard from "@/components/CourseCard";

export default function HomePage() {
  const [courses, setCourses] = useState<CourseListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCourses = useCallback(async () => {
    try {
      const data = await listCourses();
      setCourses(data);
    } catch {
      // backend might not be running yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCourses();
  }, [fetchCourses]);

  return (
    <div className="space-y-12">
      {/* Upload section */}
      <section>
        <h1 className="text-2xl font-bold mb-1">Learning Content Pipeline</h1>
        <p className="text-gray-400 mb-5 text-sm">
          Upload a course .txt file to run the full processing pipeline.
        </p>
        <UploadForm onSuccess={() => fetchCourses()} />
      </section>

      {/* Processed courses */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Processed Courses</h2>
        {loading ? (
          <p className="text-gray-400 text-sm">Loading...</p>
        ) : courses.length === 0 ? (
          <p className="text-gray-500 text-sm">
            No courses yet. Upload a .txt file to get started.
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {courses.map((c) => (
              <CourseCard key={c.slug} course={c} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
