"use client";

export function ProjectNameField({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled?: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <div className="field">
      <label htmlFor="project-name">Project name</label>
      <input
        id="project-name"
        type="text"
        placeholder="e.g. Neon Harbor"
        autoComplete="off"
        maxLength={120}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
