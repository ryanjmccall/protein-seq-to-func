import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteTitle = "Protein Atlas | West Coast Vectors";
const siteDescription =
  "Human-readable protein dossiers that connect sequence variation to structure, function, and clinical relevance.";

export const metadata: Metadata = {
  metadataBase: new URL("https://protein-seq-to-function.vercel.app"),
  title: {
    default: siteTitle,
    template: "%s | Protein Atlas",
  },
  description: siteDescription,
  keywords: [
    "protein",
    "sequence to function",
    "bioinformatics",
    "West Coast Vectors",
    "molecular biology",
    "structure function relationships",
  ],
  authors: [{ name: "West Coast Vectors" }],
  creator: "West Coast Vectors",
  publisher: "West Coast Vectors",
  openGraph: {
    title: siteTitle,
    description: siteDescription,
    url: "/",
    siteName: "Protein Atlas",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: siteTitle,
    description: siteDescription,
  },
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
