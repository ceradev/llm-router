import type { HistoryItem } from "../types";

export const HISTORY_MOCK: HistoryItem[] = [
    {
      id: "1",
      prompt: "Code review for our auth middleware and suggest hardening steps…",
      model: "GPT-4",
      timeAgo: "2h ago",
    },
    {
      id: "2",
      prompt: "Summarize this quarterly report into 5 bullet points for execs.",
      model: "Claude 3.5",
      timeAgo: "Yesterday",
    },
    {
      id: "3",
      prompt: "Draft SQL migrations for adding soft deletes to users.",
      model: "Gemini 1.5",
      timeAgo: "3d ago",
    },
  ]