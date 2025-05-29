import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AGno Showcase - Complex UIs with CopilotKit",
  description: "Demonstrating complex UI patterns with CopilotKit and AGno agents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
