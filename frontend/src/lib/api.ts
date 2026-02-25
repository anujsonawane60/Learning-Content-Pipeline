import { CourseListItem, CourseDetail, UploadResult } from "./types";

export async function uploadCourse(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch("/api/courses/upload", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export async function listCourses(): Promise<CourseListItem[]> {
  const res = await fetch("/api/courses");
  if (!res.ok) throw new Error("Failed to fetch courses");
  return res.json();
}

export async function getCourse(slug: string): Promise<CourseDetail> {
  const res = await fetch(`/api/courses/${slug}`);
  if (!res.ok) throw new Error("Course not found");
  return res.json();
}

export function jsonDownloadUrl(slug: string): string {
  return `/api/courses/${slug}/files/json`;
}

export function sqlDownloadUrl(slug: string): string {
  return `/api/courses/${slug}/files/sql`;
}
