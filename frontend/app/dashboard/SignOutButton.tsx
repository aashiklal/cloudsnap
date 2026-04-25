'use client';

import { useRouter } from 'next/navigation';
import { LogOut } from 'lucide-react';
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
      className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors"
      style={{ color: 'color-mix(in oklch, var(--header-fg) 70%, transparent)' }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLButtonElement).style.color = 'var(--header-fg)';
        (e.currentTarget as HTMLButtonElement).style.background = 'oklch(1 0 0 / 0.1)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLButtonElement).style.color = 'color-mix(in oklch, var(--header-fg) 70%, transparent)';
        (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
      }}
    >
      <LogOut className="size-3.5" />
      Sign out
    </button>
  );
}
