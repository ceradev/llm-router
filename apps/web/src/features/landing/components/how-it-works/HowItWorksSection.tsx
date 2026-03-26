import { useI18n } from "@/contexts/I18nContext"
import { IconApi, IconClock, IconCode } from "@/shared/components"

import { HowCard } from "./HowCard"

export function HowItWorksSection() {
  const { t } = useI18n()

  return (
    <section id="how-it-works" className="relative mt-12 sm:mt-14">
      <header className="mb-6 text-center sm:mb-7">
        <p className="text-xs font-semibold uppercase tracking-wider text-(--text-accent)">
          {t("howItWorksKicker")}
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-(--text-primary) sm:text-3xl">
          {t("howItWorksTitle")}
        </h2>
      </header>

      <div className="grid gap-4 sm:grid-cols-3 sm:gap-5">
        <HowCard
          icon={<IconCode className="h-5 w-5" />}
          titleKey="howItWorksCard1Title"
          descriptionKey="howItWorksCard1Desc"
        />
        <HowCard
          icon={<IconApi className="h-5 w-5" />}
          titleKey="howItWorksCard2Title"
          descriptionKey="howItWorksCard2Desc"
        />
        <HowCard
          icon={<IconClock className="h-5 w-5" />}
          titleKey="howItWorksCard3Title"
          descriptionKey="howItWorksCard3Desc"
        />
      </div>
    </section>
  )
}

