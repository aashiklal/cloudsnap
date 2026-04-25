'use client';

import { useState } from 'react';
import Image from 'next/image';
import useSWR from 'swr';
import { motion } from 'framer-motion';
import { AlertCircle, RefreshCw, ImageOff, ArrowLeft, Tag, Plus, Minus, X } from 'lucide-react';
import { listImages, modifyTags } from '@/lib/api';
import { SkeletonGrid } from '@/components/ui/SkeletonCard';
import { TagBadge } from '@/components/ui/TagBadge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Tag as TagType, SelectedImage } from '@/lib/types';

type Props = {
  onResult: (r: string) => void;
  setLoading: (v: boolean) => void;
  preselected?: SelectedImage;
  onClearPreselected?: () => void;
};

export function ModifyTagsTab({ onResult, setLoading, preselected, onClearPreselected }: Props) {
  const [picked, setPicked] = useState<SelectedImage | null>(null);
  const [action, setAction] = useState<'add' | 'remove'>('add');
  const [newTags, setNewTags] = useState(['']);
  const [tagsToRemove, setTagsToRemove] = useState<Set<string>>(new Set());
  const [error, setError] = useState('');

  const active = preselected ?? picked;

  function selectImage(img: SelectedImage) {
    setPicked(img);
    onClearPreselected?.();
    setNewTags(['']);
    setTagsToRemove(new Set());
    setError('');
  }

  function clearSelection() {
    setPicked(null);
    onClearPreselected?.();
    setNewTags(['']);
    setTagsToRemove(new Set());
    setError('');
  }

  function toggleRemove(tagName: string) {
    setTagsToRemove((prev) => {
      const next = new Set(prev);
      if (next.has(tagName)) next.delete(tagName);
      else next.add(tagName);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!active) return;

    let tagInputs: { name: string; count: string }[];
    if (action === 'add') {
      const valid = newTags.filter((n) => n.trim());
      if (!valid.length) { setError('Add at least one tag'); return; }
      tagInputs = valid.map((n) => ({ name: n.trim(), count: '1' }));
    } else {
      if (!tagsToRemove.size) { setError('Select at least one tag to remove'); return; }
      tagInputs = active.tags
        .filter((t) => tagsToRemove.has(t.tag))
        .map((t) => ({ name: t.tag, count: String(t.count) }));
    }

    setLoading(true);
    setError('');
    try {
      const result = await modifyTags(active.url, action === 'add' ? '1' : '0', tagInputs);
      onResult(result.message);
      setNewTags(['']);
      setTagsToRemove(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setLoading(false);
    }
  }

  if (!active) {
    return <ImagePicker onSelect={selectImage} />;
  }

  const filename = active.url.split('/').pop() ?? active.url;
  const currentTags: TagType[] = active.tags;

  const inputClass = 'flex-1 px-3 py-2 border border-white/[0.09] rounded-lg text-sm bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/25 focus:border-primary transition-colors';

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-lg">
      {/* Selected image bar */}
      <div className="flex items-center gap-3 p-3 rounded-xl border border-white/[0.08] bg-white/[0.03]">
        <div className="relative h-14 w-14 flex-shrink-0 rounded-lg overflow-hidden bg-white/5 ring-2 ring-primary/25">
          <Image
            src={active.presignedUrl ?? active.url}
            alt={filename}
            fill
            unoptimized
            className="object-cover"
            sizes="56px"
          />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground truncate">{filename}</p>
          <div className="flex items-center gap-1 mt-0.5">
            <Tag className="size-3 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">
              {currentTags.length} tag{currentTags.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={clearSelection}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-lg hover:bg-white/5 flex-shrink-0"
        >
          <ArrowLeft className="size-3" /> Change
        </button>
      </div>

      {/* Add / Remove toggle */}
      <div className="flex rounded-xl border border-white/[0.08] overflow-hidden bg-white/[0.02]">
        {(['add', 'remove'] as const).map((a) => (
          <button
            key={a}
            type="button"
            onClick={() => setAction(a)}
            className={cn(
              'flex-1 py-2.5 text-sm font-medium transition-all flex items-center justify-center gap-1.5',
              action === a
                ? 'brand-gradient text-white shadow-sm'
                : 'text-muted-foreground hover:bg-white/5'
            )}
          >
            {a === 'add' ? <Plus className="size-3.5" /> : <Minus className="size-3.5" />}
            {a === 'add' ? 'Add Tags' : 'Remove Tags'}
          </button>
        ))}
      </div>

      {action === 'add' && (
        <div className="space-y-2">
          {newTags.map((tag, i) => (
            <div key={i} className="flex gap-2">
              <input
                type="text"
                placeholder="Tag name (e.g. dog, car, person)"
                value={tag}
                onChange={(e) => setNewTags((p) => p.map((v, idx) => idx === i ? e.target.value : v))}
                className={inputClass}
              />
              {newTags.length > 1 && (
                <button
                  type="button"
                  onClick={() => setNewTags((p) => p.filter((_, idx) => idx !== i))}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                >
                  <X className="size-3.5" />
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() => setNewTags((p) => [...p, ''])}
            className="flex items-center gap-1.5 text-sm text-primary hover:underline font-medium"
          >
            <Plus className="size-4" /> Add another tag
          </button>
        </div>
      )}

      {action === 'remove' && (
        <div>
          {currentTags.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {currentTags.map((t) => (
                <TagBadge
                  key={t.tag}
                  label={t.tag}
                  variant={tagsToRemove.has(t.tag) ? 'removable' : 'selected'}
                  onClick={() => toggleRemove(t.tag)}
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">This image has no tags to remove.</p>
          )}
        </div>
      )}

      {error && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-destructive">
          {error}
        </motion.p>
      )}

      <Button type="submit" className="w-full sm:w-auto">
        {action === 'add' ? 'Add tags' : 'Remove selected tags'}
      </Button>
    </form>
  );
}

function ImagePicker({ onSelect }: { onSelect: (img: SelectedImage) => void }) {
  const { data: images, error, isLoading, mutate } = useSWR(
    'images',
    () => listImages(),
    { dedupingInterval: 30_000 }
  );

  if (isLoading) {
    return <SkeletonGrid count={6} />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-center">
        <AlertCircle className="size-8 text-destructive/60" />
        <p className="text-sm text-destructive">Failed to load images</p>
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
    <div className="space-y-3">
      <p className="text-sm font-medium text-foreground">Select an image to edit its tags</p>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
        {images.map((img) => {
          const filename = img.ImageURL.split('/').pop() ?? img.ImageURL;
          return (
            <motion.button
              key={img.ImageURL}
              type="button"
              whileHover={{ scale: 1.03 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              onClick={() => onSelect({ url: img.ImageURL, presignedUrl: img.PresignedURL ?? undefined, tags: img.Tags })}
              className="group relative rounded-lg overflow-hidden border-2 border-transparent hover:border-primary/50 transition-colors focus:outline-none focus:border-primary"
              style={{ background: 'oklch(0.12 0.015 264)' }}
            >
              <div className="relative aspect-square bg-white/5">
                <Image
                  src={img.PresignedURL ?? img.ImageURL}
                  alt={filename}
                  fill
                  unoptimized
                  className="object-cover group-hover:opacity-80 transition-opacity"
                  sizes="(max-width: 640px) 33vw, 20vw"
                />
              </div>
              <div className="p-1">
                <p className="text-xs text-muted-foreground truncate">{filename}</p>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
