import { cn } from '@/lib/utils';

type Variant = 'default' | 'removable' | 'selected';

type Props = {
  label: string;
  variant?: Variant;
  onClick?: () => void;
};

export function TagBadge({ label, variant = 'default', onClick }: Props) {
  const base = 'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors';
  const variants: Record<Variant, string> = {
    default: 'bg-primary/12 text-primary border border-primary/20',
    removable: 'bg-destructive/10 text-destructive line-through cursor-pointer hover:bg-destructive/20 border border-destructive/15',
    selected: 'bg-primary/15 text-primary ring-1 ring-primary/30 cursor-pointer hover:bg-primary/22 border border-primary/25',
  };

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn(base, variants[variant])}>
        {label}
      </button>
    );
  }
  return <span className={cn(base, variants[variant])}>{label}</span>;
}
