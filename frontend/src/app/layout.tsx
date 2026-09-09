import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CineGuard — Production Intelligence",
  description: "Upload a screenplay and identify production risks before they break the shoot.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
