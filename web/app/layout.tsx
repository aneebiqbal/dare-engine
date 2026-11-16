import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { ToastProvider } from "@/components/ui";
import { ThemeScript } from "@/components/theme-script";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clipdesk Missions",
  description: "The Short is written before the game is played.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${GeistSans.className} bg-bg text-text antialiased`}>
        <ThemeScript />
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
