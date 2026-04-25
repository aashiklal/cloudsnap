'use client';

import { useState } from 'react';
import Image from 'next/image';
import useSWR from 'swr';
import { motion } from 'framer-motion';
import { AlertCircle, RefreshCw, ImageOff, Images, Pencil, Trash2 } from 'lucide-react';
import { listImages, deleteImage } from '@/lib/api';
import { SkeletonGrid } from '@/components/ui/SkeletonCard';
import { TagBadge } from '@/components/ui/TagBadge';
import type { ImageRecord, SelectedImage } from '@/lib/types';

type Props = {
  onEditTags: (image: SelectedImage) => void;
};

export function GalleryTab({ onEditTags }: Props) {
  const { data: images, error, isLoading, mutate } = useSWR(
    'images',
    () => listImages(),
    { revalidateOnFocus: true, dedupingInterval: 30_000 }
  );

  if (isLoading) {
    return <SkeletonGrid count={8} />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-center">
        <AlertCircle className="size-8 text-destructive/60" />
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Failed to load images'}
        </p>
        <button
          onClick={() => mutate()}
          className="flex items-center gap-1.5 text-sm text-primary hover:underline"
        >
          <RefreshCw className="size-3.5" /> Try again
        </button>
      </div>
    );
  }

  if (!images || images.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/5 border border-white/[0.07]">
          <ImageOff className="size-8 text-muted-foreground/50" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">No images yet</p>
          <p className="text-xs text-muted-foreground mt-1">Upload your first image to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Images className="size-4 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            {images.length} image{images.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => mutate()}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors p-1 rounded hover:bg-white/5"
        >
          <RefreshCw className="size-3.5" />
          <span>Refresh</span>
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {images.map((img) => (
          <GalleryCard
            key={img.ImageURL}
            image={img}
            onEditTags={() => onEditTags({ url: img.ImageURL, presignedUrl: img.PresignedURL ?? undefined, tags: img.Tags })}
            onDeleted={() => mutate()}
          />
        ))}
      </div>
    </div>
  );
}

function GalleryCard({
  image,
  onEditTags,
  onDeleted,
}: {
  image: ImageRecord;
  onEditTags: () => void;
  onDeleted: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const filename = image.ImageURL.split('/').pop() ?? image.ImageURL;

  async function handleDelete() {
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteImage(image.ImageURL);
      onDeleted();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Delete failed');
      setDeleting(false);
    }
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className="group relative rounded-xl overflow-hidden border border-white/[0.08] bg-card transition-all duration-200"
      style={{ ['--hover-border' as string]: 'oklch(0.66 0.28 276 / 0.35)' }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = 'oklch(0.62 0.19 215 / 0.4)';
        (e.currentTarget as HTMLElement).style.boxShadow = '0 0 20px var(--primary-glow)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = '';
        (e.currentTarget as HTMLElement).style.boxShadow = '';
      }}
    >
      <div className="relative aspect-square bg-white/5">
        <Image
          src={image.PresignedURL ?? image.ImageURL}
          alt={filename}
          fill
          unoptimized
          className="object-cover"
          sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, 25vw"
        />
        {!confirming && (
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-end justify-center gap-2 p-3"
            style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.3) 50%, transparent 100%)' }}
          >
            <button
              onClick={onEditTags}
              className="flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg text-white transition-colors"
              style={{ background: 'oklch(1 0 0 / 0.12)', backdropFilter: 'blur(8px)', border: '1px solid oklch(1 0 0 / 0.15)' }}
            >
              <Pencil className="size-3" /> Edit Tags
            </button>
            <button
              onClick={() => setConfirming(true)}
              className="flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg text-white transition-colors"
              style={{ background: 'oklch(0.64 0.22 22 / 0.7)', backdropFilter: 'blur(8px)', border: '1px solid oklch(0.64 0.22 22 / 0.4)' }}
            >
              <Trash2 className="size-3" /> Delete
            </button>
          </div>
        )}
      </div>

      {confirming ? (
        <div className="p-2 border-t border-destructive/15 space-y-2" style={{ background: 'oklch(0.64 0.22 22 / 0.06)' }}>
          <p className="text-xs text-destructive font-medium">Delete this image?</p>
          {deleteError && (
            <p className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1">{deleteError}</p>
          )}
          <div className="flex gap-2">
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex-1 bg-destructive text-white text-xs font-medium py-1.5 rounded-lg hover:bg-destructive/90 disabled:opacity-50 transition-colors"
            >
              {deleting ? 'Deleting…' : 'Yes, delete'}
            </button>
            <button
              onClick={() => setConfirming(false)}
              className="flex-1 border border-white/10 text-foreground text-xs font-medium py-1.5 rounded-lg hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="p-2">
          <p className="text-xs text-foreground truncate font-medium">{filename}</p>
          {image.Tags.length === 0 ? (
            <span className="text-xs text-amber-400/80 italic">Analyzing…</span>
          ) : (
            <div className="flex flex-wrap gap-1 mt-1">
              {image.Tags.slice(0, 3).map((t) => (
                <TagBadge key={t.tag} label={t.tag} />
              ))}
              {image.Tags.length > 3 && (
                <span className="text-xs text-muted-foreground">+{image.Tags.length - 3}</span>
              )}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
