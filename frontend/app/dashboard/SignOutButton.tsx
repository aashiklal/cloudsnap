'use client';

import { useRouter } from 'next/navigation';
import { handleSignOut } from '@/lib/auth';

export function SignOutButton() {
  const router = useRouter();

  async function onClick() {
    await handleSignOut();
    router.push('/login');
  }

  return (
    <button
      onClick={onClick}
      className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
    >
      Sign out
    </button>
  );
}
