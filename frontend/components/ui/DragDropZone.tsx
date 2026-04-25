'use client';

import { useRef, useState, type DragEvent, type ChangeEvent } from 'react';
import { UploadCloud } from 'lucide-react';
import { cn } from '@/lib/utils';

type Props = {
  accept: string;
  maxSizeMB?: number;
  onFile: (file: File) => void;
  onError: (msg: string) => void;
  label?: string;
  hint?: string;
};

export function DragDropZone({ accept, maxSizeMB = 10, onFile, onError, label, hint }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  function processFile(file: File) {
    if (file.size > maxSizeMB * 1024 * 1024) {
      onError(`File is ${(file.size / (1024 * 1024)).toFixed(1)} MB — maximum is ${maxSizeMB} MB.`);
      return;
    }
    onFile(file);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    e.target.value = '';
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={cn(
        'relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-all duration-200',
        isDragging
          ? 'border-primary scale-[1.01]'
          : 'border-white/10 hover:border-primary/40 hover:bg-white/[0.02]'
      )}
      style={isDragging ? {
        boxShadow: '0 0 0 1px var(--primary), 0 0 28px var(--primary-glow)',
        background: 'oklch(0.62 0.19 215 / 0.06)',
      } : undefined}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={onChange}
      />
      <div className={cn(
        'flex h-12 w-12 items-center justify-center rounded-xl transition-all duration-200',
        isDragging ? 'brand-gradient text-white' : 'bg-white/5 text-muted-foreground'
      )}
        style={isDragging ? { boxShadow: '0 0 16px var(--primary-glow)' } : undefined}
      >
        <UploadCloud className="size-6" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-foreground">
          {label ?? 'Drop your image here'}
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {hint ?? `or click to browse — up to ${maxSizeMB} MB`}
        </p>
      </div>
    </div>
  );
}
