import { useEffect, type Dispatch, type RefObject, type SetStateAction } from "react";

export function useProvidersDismiss(
    open: boolean,
    providersOpen: boolean,
    providersRef: RefObject<HTMLDivElement | null>,
    setProvidersOpen: Dispatch<SetStateAction<boolean>>,
) {
    useEffect(() => {
        if (!open || !providersOpen) return;

        const onPointerDown = (e: PointerEvent) => {
            if (
                providersRef.current &&
                !providersRef.current.contains(e.target as Node)
            ) {
                setProvidersOpen(false);
            }
        };

        const onKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") setProvidersOpen(false);
        };

        document.addEventListener("pointerdown", onPointerDown);
        document.addEventListener("keydown", onKeyDown);

        return () => {
            document.removeEventListener("pointerdown", onPointerDown);
            document.removeEventListener("keydown", onKeyDown);
        };
    }, [open, providersOpen, providersRef, setProvidersOpen]);
}