/** Parse only the canonical course/lesson item identity; never guess from arbitrary keys. */
export function courseLearningTarget(key: string): { courseId: string; artifactId: string } | null {
  const match = /^course:([A-Za-z0-9][A-Za-z0-9_.-]{0,255}):artifact:([A-Za-z0-9][A-Za-z0-9_.-]{0,255})$/.exec(key);
  return match ? { courseId: match[1], artifactId: match[2] } : null;
}
