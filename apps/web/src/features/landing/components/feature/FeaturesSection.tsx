import { useI18n } from "@/contexts/I18nContext"
import { IconBatch, IconCheck, IconChat, IconInfo } from "@/shared/components"

import { FeatureCard } from "./FeatureCard"

export function FeaturesSection() {
  const { t } = useI18n()

  return (
    <section className="relative mt-12 sm:mt-14">
      <header className="mb-6 text-center sm:mb-7">
        <p className="text-xs font-semibold uppercase tracking-wider text-(--text-accent-secondary)">
          {t("featuresKicker")}
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-(--text-primary) sm:text-3xl">
          {t("featuresTitle")}
        </h2>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 sm:gap-5">
        <FeatureCard
          icon={<IconCheck className="h-5 w-5" />}
          titleKey="feature1Title"
          descriptionKey="feature1Desc"
        />
        <FeatureCard
          icon={<IconInfo className="h-5 w-5" />}
          titleKey="feature2Title"
          descriptionKey="feature2Desc"
        />
        <FeatureCard
          icon={<IconChat className="h-5 w-5" />}
          titleKey="feature3Title"
          descriptionKey="feature3Desc"
        />
        <FeatureCard
          icon={<IconBatch className="h-5 w-5" />}
          titleKey="feature4Title"
          descriptionKey="feature4Desc"
        />
      </div>
    </section>
  )
}

