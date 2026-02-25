import Link from "next/link";
import { CourseListItem } from "@/lib/types";

export default function CourseCard({ course }: { course: CourseListItem }) {
  return (
    <Link
      href={`/courses/${course.slug}`}
      className="block border border-gray-700 rounded-lg p-5 hover:border-gray-500 transition-colors"
    >
      <h3 className="font-semibold text-lg mb-1">{course.title}</h3>
      <p className="text-sm text-gray-400">
        {course.module_count} module{course.module_count !== 1 && "s"} &middot;{" "}
        {course.chapter_count} chapter{course.chapter_count !== 1 && "s"}
      </p>
      <div className="mt-3 flex gap-2">
        {course.has_json && (
          <span className="text-xs px-2 py-0.5 rounded bg-green-900 text-green-300">
            JSON
          </span>
        )}
        {course.has_sql && (
          <span className="text-xs px-2 py-0.5 rounded bg-purple-900 text-purple-300">
            SQL
          </span>
        )}
      </div>
    </Link>
  );
}
