'use client';

import { useState } from 'react';
import Image from 'next/image';
import useSWR from 'swr';
import { listImages, modifyTags } from '@/lib/api';
import type { Tag, SelectedImage } from '@/lib/types';

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
  const currentTags: Tag[] = active.tags;

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-lg">
      <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <div className="relative h-16 w-16 flex-shrink-0 rounded overflow-hidden bg-gray-200">
          <Image
            src={active.presignedUrl ?? active.url}
            alt={filename}
            fill
            unoptimized
            className="object-cover"
            sizes="64px"
          />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-700 truncate">{filename}</p>
          <p className="text-xs text-gray-400">{currentTags.length} tag{currentTags.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          type="button"
          onClick={clearSelection}
          className="text-xs text-gray-400 hover:text-gray-600 flex-shrink-0"
        >
          Change
        </button>
      </div>

      <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm font-medium">
        <button
          type="button"
          onClick={() => setAction('add')}
          className={`flex-1 py-2 transition-colors ${action === 'add' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
        >
          Add tags
        </button>
        <button
          type="button"
          onClick={() => setAction('remove')}
          className={`flex-1 py-2 transition-colors ${action === 'remove' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
        >
          Remove tags
        </button>
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
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {newTags.length > 1 && (
                <button
                  type="button"
                  onClick={() => setNewTags((p) => p.filter((_, idx) => idx !== i))}
                  className="text-gray-400 hover:text-red-500 text-lg leading-none"
                >
                  ×
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() => setNewTags((p) => [...p, ''])}
            className="text-sm text-blue-600 hover:underline"
          >
            + Add another tag
          </button>
        </div>
      )}

      {action === 'remove' && (
        <div>
          {currentTags.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {currentTags.map((t) => (
                <button
                  key={t.tag}
                  type="button"
                  onClick={() => toggleRemove(t.tag)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                    tagsToRemove.has(t.tag)
                      ? 'bg-red-100 border-red-300 text-red-700 line-through'
                      : 'bg-gray-100 border-gray-200 text-gray-700 hover:bg-red-50 hover:border-red-200 hover:text-red-600'
                  }`}
                >
                  {t.tag}
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">This image has no tags to remove.</p>
          )}
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
      >
        {action === 'add' ? 'Add tags' : 'Remove selected tags'}
      </button>
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
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <div className="h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        Loading your images…
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-red-600">Failed to load images</p>
        <button onClick={() => mutate()} className="text-sm text-blue-600 hover:underline">Try again</button>
      </div>
    );
  }

  if (!images || images.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-8 text-center">No images yet. Upload one to get started.</p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600 font-medium">Select an image to edit its tags</p>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
        {images.map((img) => {
          const filename = img.ImageURL.split('/').pop() ?? img.ImageURL;
          return (
            <button
              key={img.ImageURL}
              type="button"
              onClick={() => onSelect({ url: img.ImageURL, presignedUrl: img.PresignedURL ?? undefined, tags: img.Tags })}
              className="group relative rounded-lg overflow-hidden border-2 border-transparent hover:border-blue-500 transition-colors focus:outline-none focus:border-blue-500"
            >
              <div className="relative aspect-square bg-gray-100">
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
                <p className="text-xs text-gray-500 truncate">{filename}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
