import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AmplifyProvider } from '@/components/AmplifyProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'CloudSnap',
  description: 'AI-powered cloud image management — upload, tag, search, and delete images using AWS object detection.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} h-full bg-gray-50 antialiased`}>
        <AmplifyProvider>{children}</AmplifyProvider>
      </body>
    </html>
  );
}
