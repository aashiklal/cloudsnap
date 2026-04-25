import type { Metadata } from 'next';
import { Outfit } from 'next/font/google';
import './globals.css';
import { AmplifyProvider } from '@/components/AmplifyProvider';

const outfit = Outfit({ subsets: ['latin'], variable: '--font-sans', display: 'swap' });

export const metadata: Metadata = {
  title: 'CloudSnap',
  description: 'AI-powered cloud image management — upload, tag, search, and delete images using AWS object detection.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${outfit.variable} dark h-full`}>
      <body className="font-sans h-full antialiased">
        <AmplifyProvider>{children}</AmplifyProvider>
      </body>
    </html>
  );
}
