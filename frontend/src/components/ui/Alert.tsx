export function Alert({
  variant = "error",
  title,
  children,
}: {
  variant?: "error" | "info";
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`alert alert-${variant}`} role="alert">
      {title ? <p className="alert-title">{title}</p> : null}
      <div>{children}</div>
    </div>
  );
}
