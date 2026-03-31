import { motion } from "framer-motion"

import { useI18n } from "@/contexts/I18nContext"

export function ResultsModelsLegend({
  variants,
}: Readonly<{
  variants: object
}>) {
  const { t } = useI18n()

  return (
    <motion.section
      variants={variants}
      className="mt-4 rounded-2xl border border-(--border-subtle) bg-(--surface-glass) p-4 text-sm leading-relaxed text-(--text-muted) shadow-(--shadow-elevated) backdrop-blur-xl sm:p-5"
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-muted)">
        {t("modelsLegendTitle")}
      </p>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        <li>
          <span className="font-medium text-(--text-primary)">{t("quality")}: </span>
          {t("legendQuality")}
        </li>
        <li>
          <span className="font-medium text-(--text-primary)">{t("cost")}: </span>
          {t("legendCost")}
        </li>
        <li>
          <span className="font-medium text-(--text-primary)">{t("speed")}: </span>
          {t("legendSpeed")}
        </li>
        <li>
          <span className="font-medium text-(--text-primary)">{t("labelOutputTokens")}: </span>
          {t("legendTokens")}
        </li>
        <li className="sm:col-span-2">
          <span className="font-medium text-(--text-primary)">{t("labelContext")}: </span>
          {t("legendContext")}
        </li>
      </ul>

      <p className="mt-5 text-[11px] font-semibold uppercase tracking-wider text-(--text-muted)">
        {t("modelsLegendMoreTitle")}
      </p>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        <li>
          <span className="font-medium text-(--text-primary)">{t("scoreLabel")}: </span>
          {t("legendScore")}
        </li>
        <li>
          <span className="font-medium text-(--text-primary)">{t("ratingLabel")}: </span>
          {t("legendRating")}
        </li>
        <li>
          <span className="font-medium text-(--text-primary)">{t("pricingLabel")}: </span>
          {t("legendPricing")}
        </li>
        <li>
          <span className="font-medium text-(--text-primary)">{t("latency")}: </span>
          {t("legendLatency")}
        </li>
        <li>
          <span className="font-medium text-(--text-primary)">
            {t("tierFree")}/{t("tierPremium")}:{" "}
          </span>
          {t("legendTiers")}
        </li>
        <li>
          <span className="font-medium text-(--text-primary)">
            {t("publicStatus_verified")}/{t("publicStatus_provisional")}:{" "}
          </span>
          {t("legendStatus")}
        </li>
      </ul>
    </motion.section>
  )
}

