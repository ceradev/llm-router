import { useEffect, type RefObject } from "react";

export function useModalEscapeClose(open: boolean, onClose: () => void) {
    useEffect(() => {
        if (!open) return;
        const onKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        document.addEventListener("keydown", onKeyDown);
        return () => document.removeEventListener("keydown", onKeyDown);
    }, [open, onClose]);
}

export function useModalFocusRestore(
    open: boolean,
    closeBtnRef: RefObject<HTMLButtonElement | null>,
) {
    useEffect(() => {
        if (!open) return;
        const prev = document.activeElement as HTMLElement | null;
        const timerId = globalThis.setTimeout(() => closeBtnRef.current?.focus(), 0);
        return () => {
            globalThis.clearTimeout(timerId);
            prev?.focus?.();
        };
    }, [open, closeBtnRef]);
}
