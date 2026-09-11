// src/api/topics.js
import { apiFetch } from "./client";

export function listTopics() {
  return apiFetch("/topics");
}