'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { fetchAuthSession } from 'aws-amplify/auth';
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
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <Link href="/dashboard" className="text-xl font-semibold text-gray-900 tracking-tight">
          CloudSnap
        </Link>
        <SignOutButton />
      </header>
      <main className="flex-1 p-6 max-w-5xl mx-auto w-full">{children}</main>
    </div>
  );
}
