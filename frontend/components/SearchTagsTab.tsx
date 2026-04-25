'use client';

import { useState } from 'react';
import { searchByTags } from '@/lib/api';
import type { TagInput, SearchResult } from '@/lib/types';

type Props = { onResult: (r: SearchResult[] | string) => void; setLoading: (v: boolean) => void };

export function SearchTagsTab({ onResult, setLoading }: Props) {
  const [tags, setTags] = useState<TagInput[]>([{ name: '', count: '1' }]);
  const [error, setError] = useState('');

  function addTag() {
    setTags((prev) => [...prev, { name: '', count: '1' }]);
  }

  function removeTag(i: number) {
    setTags((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateTag(i: number, field: keyof TagInput, value: string) {
    setTags((prev) => prev.map((t, idx) => idx === i ? { ...t, [field]: value } : t));
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const valid = tags.filter((t) => t.name.trim() && t.count);
    if (!valid.length) { setError('Add at least one tag'); return; }
    setLoading(true);
    setError('');
    try {
      const results = await searchByTags(valid);
      onResult(results);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSearch} className="space-y-4 max-w-lg">
      <div className="space-y-2">
        {tags.map((tag, i) => (
          <div key={i} className="flex gap-2 items-center">
            <input
              type="text"
              placeholder="Tag name (e.g. dog)"
              value={tag.name}
              onChange={(e) => updateTag(i, 'name', e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="number"
              placeholder="Min count"
              min="1"
              value={tag.count}
              onChange={(e) => updateTag(i, 'count', e.target.value)}
              className="w-28 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {tags.length > 1 && (
              <button
                type="button"
                onClick={() => removeTag(i)}
                className="text-gray-400 hover:text-red-500 text-lg leading-none"
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={addTag}
        className="text-sm text-blue-600 hover:underline"
      >
        + Add tag
      </button>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
      >
        Search
      </button>
    </form>
  );
}
