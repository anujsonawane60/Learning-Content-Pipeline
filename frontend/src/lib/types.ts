export interface CourseListItem {
  slug: string;
  title: string;
  module_count: number;
  chapter_count: number;
  has_json: boolean;
  has_sql: boolean;
}

export interface Chapter {
  title: string;
  slug: string;
  description: string;
  content_data: { type: string; body: string };
  chapter_type: string;
  is_published: boolean;
  is_free: boolean;
  is_preview: boolean;
  estimated_duration_minutes: number | null;
  requires_activity: boolean;
  min_activities_required: number;
}

export interface Module {
  title: string;
  slug: string;
  description: string;
  is_published: boolean;
  is_preview: boolean;
  estimated_duration_hours: number | null;
  chapters: Chapter[];
}

export interface CourseDetail {
  course_title: string;
  course_slug: string;
  course_description: string;
  modules: Module[];
}

export interface UploadResult {
  course_slug: string;
  message: string;
}
