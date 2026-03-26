import { IconInfo } from "@/shared/components/icons";

export function SectionLabel({
    children,
    hint,
}: Readonly<{
    children: string;
    hint: string;
}>) {
    return (
        <div className="mb-2.5 flex items-center gap-1.5">
            <span className="text-xs font-medium tracking-wide text-(--text-muted)">
                {children}
            </span>
            <span className="group relative inline-flex">
                <button
                    type="button"
                    className="rounded p-0.5 text-(--text-muted) opacity-60 transition-colors hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-(--ring-focus)"
                    aria-label={hint}
                >
                    <IconInfo className="h-3.5 w-3.5" />
                </button>
                <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 w-56 -translate-x-1/2 rounded-lg border border-(--border-subtle) bg-(--bg-base)/95 px-2.5 py-2 text-xs leading-snug text-(--text-primary) opacity-0 shadow-lg backdrop-blur-md transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                    {hint}
                </span>
            </span>
        </div>
    );
}