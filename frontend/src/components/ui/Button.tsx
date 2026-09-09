import type { ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
  loading?: boolean;
}

export function Button({ variant = "primary", loading, children, disabled, ...rest }: Props) {
  return (
    <button
      className={`btn btn-${variant}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? "Working…" : children}
    </button>
  );
}
