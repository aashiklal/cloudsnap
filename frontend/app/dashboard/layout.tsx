import Link from 'next/link';
import { SignOutButton } from './SignOutButton';

export const metadata = {
  title: 'Dashboard — CloudSnap',
  description: 'Manage your images with AI-powered tagging and search',
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
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
