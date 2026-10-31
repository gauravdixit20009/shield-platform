import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SHIELD — Law Enforcement Intelligence Platform',
  description: 'Secure Hub for Intelligence, Enforcement & Law Data',
  robots: 'noindex, nofollow',  // Never indexed by search engines
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
        <meta httpEquiv="X-Frame-Options" content="DENY" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        {/* Prevent screenshots in mobile browsers */}
        <meta name="mobile-web-app-capable" content="yes" />
      </head>
      <body className="bg-gray-950 antialiased">{children}</body>
    </html>
  );
}
