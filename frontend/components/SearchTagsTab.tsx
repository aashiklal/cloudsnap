'use client';

import { useState } from 'react';
import { X, Plus, Search } from 'lucide-react';
import { searchByTags } from '@/lib/api';
import { Button } from '@/components/ui/button';
import type { TagInput, SearchResult } from '@/lib/types';

type Props = { onResult: (r: SearchResult[] | string) => void; setLoading: (v: boolean) => void };

const inputClass = 'px-3 py-2 border border-white/[0.09] rounded-lg text-sm bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/25 focus:border-primary transition-colors';

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
      <div>
        <p className="text-sm font-medium text-foreground">Search by tags</p>
        <p className="text-xs text-muted-foreground mt-0.5">Find images that contain all specified tags</p>
      </div>

      <div className="space-y-2">
        {tags.map((tag, i) => (
          <div key={i} className="flex gap-2 items-center">
            <input
              type="text"
              placeholder="Tag name (e.g. dog)"
              value={tag.name}
              onChange={(e) => updateTag(i, 'name', e.target.value)}
              className={`flex-1 ${inputClass}`}
            />
            <input
              type="number"
              placeholder="Min count"
              min="1"
              value={tag.count}
              onChange={(e) => updateTag(i, 'count', e.target.value)}
              className={`w-28 ${inputClass}`}
            />
            {tags.length > 1 && (
              <button
                type="button"
                onClick={() => removeTag(i)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={addTag}
        className="flex items-center gap-1.5 text-sm text-primary hover:underline font-medium"
      >
        <Plus className="size-4" /> Add tag
      </button>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button type="submit" className="w-full sm:w-auto">
        <Search className="size-3.5 mr-1.5" /> Search
      </Button>
    </form>
  );
}
