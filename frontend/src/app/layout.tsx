import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ProjectProvider } from "@/context/ProjectContext";
import { LanguageProvider } from "@/context/LanguageContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Agent 4 BA",
  description: "Assistant IA pour la gestion de backlog avec Agent 4 BA",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <LanguageProvider>
          <ProjectProvider>{children}</ProjectProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
