// src/api/topics.js
import { apiFetch } from "./client";

export function listTopics() {
  return apiFetch("/topics");
}

export function getTopicOverview() {
  return apiFetch("/topics/overview");
}