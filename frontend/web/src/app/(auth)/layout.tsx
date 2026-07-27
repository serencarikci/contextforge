import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
    return (
        <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
            <div
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_color-mix(in_oklab,var(--primary)_18%,transparent),_transparent_55%),linear-gradient(160deg,_color-mix(in_oklab,var(--accent)_10%,transparent),_transparent_40%,_color-mix(in_oklab,var(--primary)_8%,transparent))]"
            />
            <div className="relative z-10 w-full max-w-md">{children}</div>
        </div>
    );
}
