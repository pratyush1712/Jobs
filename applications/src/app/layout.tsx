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

export const metadata: Metadata = {
  title: "Job Tracker",
  description: "Local-first job application tracker",
};

/**
 * Inline script that runs before React hydrates to apply the saved theme.
 * This prevents the flash of the wrong theme on page load.
 */
const themeScript = `
  (function() {
    try {
      var stored = localStorage.getItem('jt-theme');
      var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      var theme = stored === 'dark' || stored === 'light' ? stored : (prefersDark ? 'dark' : 'light');
      if (theme === 'dark') document.documentElement.classList.add('dark');
    } catch (e) {}
  })();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full`}
      suppressHydrationWarning
    >
      {/* suppressHydrationWarning is needed because the inline script mutates the class
          before React hydrates, causing a mismatch that would otherwise warn. */}
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="h-full min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
