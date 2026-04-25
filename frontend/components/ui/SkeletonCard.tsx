import { cn } from '@/lib/utils';

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('rounded-xl border border-white/[0.07] bg-card overflow-hidden', className)}>
      <div className="aspect-square bg-white/5 animate-pulse" />
      <div className="p-2 space-y-1.5">
        <div className="h-2.5 bg-white/5 animate-pulse rounded-full w-3/4" />
        <div className="h-2 bg-white/5 animate-pulse rounded-full w-1/2" />
      </div>
    </div>
  );
}

export function SkeletonGrid({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
