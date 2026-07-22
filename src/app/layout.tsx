import type { Metadata } from "next";
import { Heebo, Geist } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const heebo = Heebo({ subsets: ["hebrew"], weight: ["300", "400", "500", "600", "700"] });

export const metadata: Metadata = {
  title: "מעקב תיק מניות | Portfolio Tracker",
  description: "אפליקציה למעקב אחר תיק מניות, רווחים, הפסדים ואחוזי שינוי",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="he" dir="rtl" className={cn("font-sans", geist.variable)}>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebApplication",
              name: "Portfolio Tracker",
              applicationCategory: "FinanceApplication",
              operatingSystem: "Any",
              description: "Interactive portfolio tracker for viewing stocks.",
              offers: {
                "@type": "Offer",
                price: "0",
              },
            }),
          }}
        />
      </head>
      <body className={`${heebo.className} min-h-screen antialiased`}>
        {children}
      </body>
    </html>
  );
}
