import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "India Mutual Fund Finder",
  description: "Objective, data-driven mutual fund recommendation & analytics tool",
};

// Runs before paint so the toggled theme applies immediately — no OS lookup,
// no flash of the wrong theme on load. Light is the default for new visitors.
const THEME_INIT = `(function(){try{if(localStorage.getItem('theme')==='dark')document.documentElement.classList.add('dark')}catch(e){}})()`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
