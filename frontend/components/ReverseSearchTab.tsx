'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { ScanSearch } from 'lucide-react';
import { searchByImage } from '@/lib/api';
import { DragDropZone } from '@/components/ui/DragDropZone';
import type { SearchResult } from '@/lib/types';

type Props = { onResult: (r: SearchResult[] | string) => void; setLoading: (v: boolean) => void };

export function ReverseSearchTab({ onResult, setLoading }: Props) {
  const [error, setError] = useState('');

  async function handleFile(file: File) {
    setError('');
    setLoading(true);
    try {
      const results = await searchByImage(file);
      onResult(results);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 max-w-lg">
      <div
        className="flex items-start gap-3 p-4 rounded-xl border border-primary/15"
        style={{ background: 'oklch(0.62 0.19 215 / 0.06)' }}
      >
        <ScanSearch className="size-5 text-primary flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-foreground">Visual Similarity Search</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Upload a query image to find visually similar images in your library using AWS Rekognition object detection.
          </p>
        </div>
      </div>

      <DragDropZone
        accept="image/jpeg,image/png,image/gif,image/webp"
        maxSizeMB={10}
        onFile={handleFile}
        onError={setError}
        label="Drop a query image"
        hint="Search starts automatically on selection"
      />

      {error && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-destructive">
          {error}
        </motion.p>
      )}
    </div>
  );
}
