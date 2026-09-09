import type { ReactNode } from "react";

export function Card({
  title,
  children,
  labelledBy,
}: {
  title?: string;
  children: ReactNode;
  labelledBy?: string;
}) {
  return (
    <section className="card" aria-labelledby={labelledBy}>
      {title ? (
        <h2 id={labelledBy} className="card-title">
          {title}
        </h2>
      ) : null}
      {children}
    </section>
  );
}
