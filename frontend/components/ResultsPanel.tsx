'use client';

import Image from 'next/image';
import { motion } from 'framer-motion';
import { Loader2, SearchX, ExternalLink, Settings2, CheckCircle2 } from 'lucide-react';
import type { ProcessingStatus, SelectedImage, SearchResult } from '@/lib/types';

type Props = {
  result: SearchResult[] | string | null;
  isLoading: boolean;
  onSelect?: (image: SelectedImage) => void;
};

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05, delayChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, scale: 0.92, y: 8 },
  visible: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.2 } },
};

export function ResultsPanel({ result, isLoading, onSelect }: Props) {
  if (!isLoading && result === null) return null;

  return (
    <div className="bg-card rounded-xl border border-white/[0.08] p-6"
      style={{ boxShadow: 'inset 0 1px 0 oklch(1 0 0 / 0.05), 0 1px 3px oklch(0 0 0 / 0.3)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold">
          <span className="brand-gradient-text">Results</span>
        </h3>
        {Array.isArray(result) && result.length > 0 && (
          <span className="text-xs bg-primary/15 text-primary border border-primary/20 rounded-full px-2.5 py-0.5 font-medium">
            {result.length} found
          </span>
        )}
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
          <Loader2 className="size-4 animate-spin text-primary" />
          Processing your request…
        </div>
      )}

      {!isLoading && typeof result === 'string' && (
        <p className="text-sm text-foreground">{result}</p>
      )}

      {!isLoading && Array.isArray(result) && result.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <SearchX className="size-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">No matching images found</p>
        </div>
      )}

      {!isLoading && Array.isArray(result) && result.length > 0 && (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3"
        >
          {result.map((item) => (
            <motion.div key={item.imageUrl} variants={itemVariants}>
              <ImageCard
                imageUrl={item.imageUrl}
                presignedUrl={item.presignedUrl}
                processingStatus={item.processingStatus ?? 'ready'}
                onSelect={onSelect ? () => onSelect({
                  url: item.imageUrl,
                  presignedUrl: item.presignedUrl,
                  tags: [],
                  processingStatus: item.processingStatus ?? 'ready',
                }) : undefined}
              />
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}

function ImageCard({
  imageUrl,
  presignedUrl,
  processingStatus,
  onSelect,
}: {
  imageUrl: string;
  presignedUrl: string;
  processingStatus: ProcessingStatus;
  onSelect?: () => void;
}) {
  const filename = imageUrl.split('/').pop() ?? imageUrl;
  return (
    <div
      className="group rounded-xl overflow-hidden border border-white/[0.08] bg-card transition-all duration-200 hover:border-primary/30"
      style={{ ['--hover-shadow' as string]: '0 0 16px var(--primary-glow)' }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = '0 0 16px var(--primary-glow)'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = ''; }}
    >
      <a href={presignedUrl} target="_blank" rel="noopener noreferrer" className="block relative">
        <div className="relative aspect-square bg-white/5">
          <Image
            src={presignedUrl}
            alt="Search result"
            fill
            unoptimized
            className="object-cover group-hover:opacity-90 transition-opacity"
            sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, 25vw"
          />
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.6) 0%, transparent 50%)' }}
          />
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="rounded-md p-1" style={{ background: 'oklch(0 0 0 / 0.5)', backdropFilter: 'blur(4px)' }}>
              <ExternalLink className="size-3 text-white" />
            </div>
          </div>
          <div className="absolute left-2 top-2">
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/25 bg-emerald-500/16 px-2 py-0.5 text-[11px] font-medium text-emerald-300 backdrop-blur-sm">
              <CheckCircle2 className="size-3" />
              {processingStatus === 'ready' ? 'Ready' : processingStatus}
            </span>
          </div>
        </div>
      </a>
      <div className="flex items-center justify-between px-2.5 py-2">
        <p className="text-xs text-muted-foreground truncate flex-1">{filename}</p>
        {onSelect && (
          <button
            onClick={onSelect}
            className="flex items-center gap-1 text-xs text-primary hover:underline ml-2 flex-shrink-0"
          >
            <Settings2 className="size-3" /> Manage
          </button>
        )}
      </div>
    </div>
  );
}
