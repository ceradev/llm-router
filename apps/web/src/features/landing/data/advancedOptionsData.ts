import type { TranslationKey } from "@/i18n/translations";
import type { Priority, ResponseDepth, UseCaseId } from "../types";

export const USE_CASE_IDS: { id: UseCaseId; titleKey: TranslationKey }[] = [
  { id: "ide", titleKey: "useCaseIde" },
  { id: "api", titleKey: "useCaseApi" },
  { id: "chatbot", titleKey: "useCaseChatbot" },
  { id: "batch", titleKey: "useCaseBatch" },
];

export const PROVIDERS = ["OpenAI", "Anthropic", "Google"] as const;

export const PRIORITY_OPTIONS: Priority[] = ["quality", "speed", "cost"];

export const RESPONSE_DEPTH_OPTIONS: ResponseDepth[] = [
  "short",
  "balanced",
  "detailed",
];

export const DEPTH_KEY_BY_VALUE: Record<ResponseDepth, TranslationKey> = {
  short: "depthShort",
  balanced: "depthBalanced",
  detailed: "depthDetailed",
};
