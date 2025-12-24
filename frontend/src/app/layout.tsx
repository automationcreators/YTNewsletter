import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/Providers';
import { Navigation } from '@/components/layout/Navigation';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'YouTube Newsletter - AI Video Summaries',
  description: 'Get weekly AI-powered summaries of your favorite YouTube channels delivered to your inbox.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased bg-gray-50`}>
        <Providers>
          <Navigation />
          <main className="lg:pl-64 pt-14 lg:pt-0 min-h-screen">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
