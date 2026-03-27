import { motion, useReducedMotion, type Transition } from "framer-motion";
import {
    useId,
    useRef,
    useState,
} from "react";
import { useI18n } from "@/contexts/I18nContext";
import { cn } from "@/lib/cn";
import { SectionLabel } from "@/features/landing/components/advanced-options";
import { IconChevronDown } from "@/shared/components";
import type {Priority, ResponseDepth, UseCaseId } from "@/features/landing/types";
import { PROVIDERS, USE_CASE_IDS, PRIORITY_OPTIONS, RESPONSE_DEPTH_OPTIONS, DEPTH_KEY_BY_VALUE } from "@/features/landing/data";
import { useModalFocusRestore, useModalEscapeClose, useProvidersDismiss } from "@/features/landing/hooks";

type Props = {
    open: boolean;
    onClose: () => void;
    onApply: () => void;
    priority: Priority;
    setPriority: (p: Priority) => void;
    useCases: Set<UseCaseId>;
    toggleUseCase: (id: UseCaseId) => void;
    providers: Set<string>;
    toggleProvider: (p: string) => void;
    responseDepth: ResponseDepth;
    setResponseDepth: (d: ResponseDepth) => void;
};

export function AdvancedOptionsModal({
    open,
    onClose,
    onApply,
    priority,
    setPriority,
    useCases,
    toggleUseCase,
    providers,
    toggleProvider,
    responseDepth,
    setResponseDepth,
}: Readonly<Props>) {
    const { t } = useI18n();
    const reduceMotion = useReducedMotion() ?? false;
    const closeBtnRef = useRef<HTMLButtonElement>(null);
    const [providersOpen, setProvidersOpen] = useState(false);
    const providersRef = useRef<HTMLDivElement>(null);
    const providersListId = useId();
    const selectedProviders = PROVIDERS.filter((name) => providers.has(name));

    useModalFocusRestore(open, closeBtnRef);
    useModalEscapeClose(open, onClose);
    useProvidersDismiss(open, providersOpen, providersRef, setProvidersOpen);

    const overlayT: Transition = reduceMotion
        ? { duration: 0 }
        : { duration: 0.12 };
    const dialogT: Transition = reduceMotion
        ? { duration: 0 }
        : { type: "tween", duration: 0.14, ease: "easeOut" };
    const segmentedBgClass =
        "bg-[rgba(255,255,255,0.36)] dark:bg-(--segment-bg)";
    const segmentedActivePillClass =
        "bg-[rgba(255,255,255,0.56)] dark:bg-(--surface-glass-hover) shadow-[0_0_18px_rgba(59,130,246,0.2)]";
    const useCaseOnClass =
        "bg-[rgba(255,255,255,0.68)] dark:bg-(--surface-glass-hover) text-(--text-primary) shadow-[0_0_14px_rgba(59,130,246,0.16)]";
    const useCaseOffClass =
        "text-(--text-muted) hover:bg-[rgba(255,255,255,0.5)] dark:hover:bg-(--surface-glass-hover) hover:text-(--text-primary)";
    const providerTagClass =
        "border-[#3B82F6]/35 bg-[rgba(255,255,255,0.66)] dark:bg-(--surface-glass)";
    const providerListClass =
        "bg-[rgba(255,255,255,0.48)] dark:bg-(--surface-glass)";
    const providerRowOnClass =
        "bg-[rgba(255,255,255,0.68)] dark:bg-(--surface-glass-hover) text-(--text-primary)";
    const providerRowOffClass =
        "text-(--text-muted) hover:bg-[rgba(255,255,255,0.5)] dark:hover:bg-(--surface-glass-hover) hover:text-(--text-primary)";

    if (!open) return null;

    return (
        <motion.div
            className="fixed inset-0 z-50 grid place-items-center px-4 py-8 sm:px-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={overlayT}
            onPointerDown={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
        >
            <motion.div
                aria-hidden
                className={cn(
                    "absolute inset-0",
                    "bg-(--scrim)",
                )}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={overlayT}
            />

            <motion.section
                role="dialog"
                aria-modal="true"
                aria-label={t("advancedOptions")}
                initial={{ opacity: 0, scale: 0.98, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.99, y: 8 }}
                transition={dialogT}
                className="relative z-10 w-full max-w-2xl overflow-hidden rounded-3xl border border-(--border-subtle) bg-[rgba(255,255,255,0.92)] dark:bg-[#0b1220] shadow-(--shadow-elevated)"
                onPointerDown={(e) => e.stopPropagation()}
            >
                <header className="flex items-center justify-between gap-4 border-b border-(--border-subtle) px-5 py-4 sm:px-6 sm:py-5">
                    <div className="min-w-0">
                        <h2 className="truncate text-base font-semibold tracking-tight text-(--text-primary) sm:text-lg">
                            {t("advancedOptions")}
                        </h2>
                    </div>
                    <button
                        ref={closeBtnRef}
                        type="button"
                        onClick={onClose}
                        className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-(--border-subtle) bg-(--surface-glass) text-(--text-muted) transition-colors hover:bg-(--surface-glass-hover) hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
                        aria-label={t("close")}
                    >
                        <span className="text-lg leading-none">×</span>
                    </button>
                </header>

                <div className="max-h-[min(70vh,640px)] overflow-y-auto p-5 sm:p-6">
                    <div className="relative overflow-visible rounded-2xl p-5 sm:p-6">
                        <div className="relative space-y-6">
                            <div>
                                <SectionLabel hint={t("priorityHint")}>
                                    {t("priority")}
                                </SectionLabel>
                                <div
                                    className={cn(
                                        "grid grid-cols-3 rounded-full border border-(--border-subtle) p-1",
                                        segmentedBgClass,
                                    )}
                                    role="tablist"
                                    aria-label="Routing priority"
                                >
                                    {PRIORITY_OPTIONS.map((p) => (
                                        <button
                                            key={p}
                                            type="button"
                                            role="tab"
                                            aria-selected={priority === p}
                                            onClick={() => setPriority(p)}
                                            className={cn(
                                                "relative rounded-full px-4 py-2 text-sm font-medium capitalize transition-colors duration-200",
                                                priority === p
                                                    ? "text-(--text-primary)"
                                                    : "text-(--text-muted) hover:opacity-80",
                                            )}
                                        >
                                            {priority === p ? (
                                                <span
                                                    className={cn(
                                                        "absolute inset-0 rounded-full",
                                                        segmentedActivePillClass,
                                                    )}
                                                />
                                            ) : null}
                                            <span className="relative z-10">
                                                {t(p as "quality" | "speed" | "cost")}
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <SectionLabel hint={t("useCaseHint")}>
                                    {t("useCase")}
                                </SectionLabel>
                                <div
                                    className={cn(
                                        "grid grid-cols-4 gap-1.5 rounded-xl border border-(--border-subtle) p-1.5",
                                        segmentedBgClass,
                                    )}
                                >
                                    {USE_CASE_IDS.map(({ id, titleKey }) => {
                                        const on = useCases.has(id);
                                        return (
                                            <button
                                                key={id}
                                                type="button"
                                                onClick={() => toggleUseCase(id)}
                                                className={cn(
                                                    "rounded-lg px-3 py-2.5 text-center text-sm font-medium transition-all duration-200 sm:px-4",
                                                    on ? useCaseOnClass : useCaseOffClass,
                                                )}
                                            >
                                                {t(titleKey)}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div>
                                <SectionLabel hint={t("providersHint")}>
                                    {t("preferredProviders")}
                                </SectionLabel>
                                <div ref={providersRef} className="relative mt-0.5">
                                    <button
                                        type="button"
                                        className={cn(
                                            "flex w-full items-center justify-between gap-2 rounded-xl border border-(--border-subtle) p-2 text-left",
                                            segmentedBgClass,
                                        )}
                                        onClick={() => setProvidersOpen((v) => !v)}
                                        aria-expanded={providersOpen}
                                        aria-controls={providersListId}
                                        aria-label={t("preferredProviders")}
                                    >
                                        <div className="flex min-h-11 flex-1 flex-wrap items-center gap-2.5">
                                            {selectedProviders.length > 0 ? (
                                                selectedProviders.map((name) => (
                                                    <span
                                                        key={name}
                                                        className={cn(
                                                            "rounded-lg border px-3.5 py-2 text-sm font-medium text-(--text-primary)",
                                                            providerTagClass,
                                                        )}
                                                    >
                                                        {name}
                                                    </span>
                                                ))
                                            ) : (
                                                <span className="px-2 text-sm text-(--text-muted)/90">
                                                    {t("preferredProviders")}
                                                </span>
                                            )}
                                        </div>
                                        <span
                                            className={cn(
                                                "rounded-md p-2 text-(--text-muted) transition-colors hover:text-(--text-primary)",
                                                "hover:bg-(--surface-glass-hover)",
                                            )}
                                        >
                                            <IconChevronDown
                                                className={cn(
                                                    "h-5 w-5 transition-transform",
                                                    providersOpen ? "rotate-180" : "",
                                                )}
                                            />
                                        </span>
                                    </button>

                                    {providersOpen ? (
                                        <ul
                                            id={providersListId}
                                            className={cn(
                                                "absolute left-0 right-0 top-[calc(100%+0.45rem)] z-20 rounded-xl border border-(--border-subtle) p-2 shadow-lg backdrop-blur-md",
                                                providerListClass,
                                            )}
                                        >
                                            {PROVIDERS.map((name) => {
                                                const on = providers.has(name);
                                                return (
                                                    <li key={name} className="mb-1 last:mb-0">
                                                        <button
                                                            type="button"
                                                            onClick={() => toggleProvider(name)}
                                                            className={cn(
                                                                "flex w-full items-center justify-between rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors",
                                                                on ? providerRowOnClass : providerRowOffClass,
                                                            )}
                                                        >
                                                            <span>{name}</span>
                                                            <span
                                                                className={cn(
                                                                    "h-2.5 w-2.5 rounded-full transition-colors",
                                                                    on
                                                                        ? "bg-[#3B82F6]"
                                                                        : "bg-transparent ring-1 ring-(--border-subtle)",
                                                                )}
                                                            />
                                                        </button>
                                                    </li>
                                                );
                                            })}
                                        </ul>
                                    ) : null}
                                </div>
                            </div>

                            <div>
                                <SectionLabel hint={t("responseDepthHint")}>
                                    {t("responseDepth")}
                                </SectionLabel>
                                <div
                                    className={cn(
                                        "grid grid-cols-3 rounded-full border border-(--border-subtle) p-1",
                                        segmentedBgClass,
                                    )}
                                    role="tablist"
                                    aria-label={t("responseDepth")}
                                >
                                    {RESPONSE_DEPTH_OPTIONS.map((d) => (
                                        <button
                                            key={d}
                                            type="button"
                                            role="tab"
                                            aria-selected={responseDepth === d}
                                            onClick={() => setResponseDepth(d)}
                                            className={cn(
                                                "relative rounded-full px-4 py-2 text-sm font-medium transition-colors duration-200",
                                                responseDepth === d
                                                    ? "text-(--text-primary)"
                                                    : "text-(--text-muted) hover:opacity-80",
                                            )}
                                        >
                                            {responseDepth === d ? (
                                                <span
                                                    className={cn(
                                                        "absolute inset-0 rounded-full",
                                                        segmentedActivePillClass,
                                                    )}
                                                />
                                            ) : null}
                                            <span className="relative z-10">
                                                {t(DEPTH_KEY_BY_VALUE[d])}
                                            </span>
                                        </button>
                                    ))}
                                </div>
                                <p className="mt-2.5 text-sm text-(--text-muted)">
                                    {t("responseDepthHelper")}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <footer className="flex flex-col gap-3 border-t border-(--border-subtle) px-5 py-4 sm:flex-row sm:items-center sm:justify-end sm:px-6 sm:py-5">
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-xl px-5 py-3 text-sm font-medium text-(--text-muted) transition-colors hover:text-(--text-primary) focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-subtle)"
                    >
                        {t("close")}
                    </button>
                    <motion.button
                        type="button"
                        onClick={onApply}
                        whileHover={
                            reduceMotion
                                ? undefined
                                : { scale: 1.02, backgroundPosition: "100% 50%" }
                        }
                        whileTap={reduceMotion ? undefined : { scale: 0.98 }}
                        transition={{ type: "spring", stiffness: 420, damping: 26 }}
                        className="relative overflow-hidden rounded-xl bg-[linear-gradient(135deg,#3B82F6,#1E40AF)] bg-size-[200%_200%] bg-left px-6 py-3 text-sm font-semibold text-white shadow-[0_12px_40px_rgba(59,130,246,0.25)] focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
                    >
                        <span className="relative z-10">{t("apply")}</span>
                        <motion.span
                            className="absolute inset-0 bg-linear-to-r from-white/0 via-white/10 to-white/0"
                            initial={{ x: "-100%" }}
                            whileHover={reduceMotion ? undefined : { x: "100%" }}
                            transition={{ duration: 0.6 }}
                        />
                    </motion.button>
                </footer>
            </motion.section>
        </motion.div>
    );
}
