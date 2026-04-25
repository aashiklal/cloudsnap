'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { fetchAuthSession } from 'aws-amplify/auth';
import { Cloud } from 'lucide-react';
import { SignOutButton } from './SignOutButton';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    fetchAuthSession()
      .then((s) => { if (!s.tokens) router.replace('/login'); })
      .catch(() => router.replace('/login'));
  }, [router]);

  return (
    <div className="min-h-screen flex flex-col">
      <header
        className="sticky top-0 z-50 glass"
        style={{ borderBottom: '1px solid var(--header-border)' }}
      >
        <div className="px-6 py-3.5 flex items-center justify-between max-w-6xl mx-auto w-full">
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg brand-gradient"
              style={{ boxShadow: '0 0 16px var(--primary-glow)' }}
            >
              <Cloud className="size-4 text-white" />
            </div>
            <span className="text-base font-semibold tracking-tight" style={{ color: 'var(--header-fg)' }}>
              CloudSnap
            </span>
          </Link>
          <SignOutButton />
        </div>
      </header>
      <main className="flex-1 p-6 max-w-6xl mx-auto w-full">{children}</main>
    </div>
  );
}
