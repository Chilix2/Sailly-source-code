import type { Metadata } from 'next';
import './globals.css';
import { LayoutShell } from '@/components/LayoutShell';

export const metadata: Metadata = {
  title: 'Sailly Command Center — Voice AI Operations',
  description: 'Real-time monitoring and operations dashboard for voice AI',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-transparent text-black font-sans">
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}

