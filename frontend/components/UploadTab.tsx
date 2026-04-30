'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { useSWRConfig } from 'swr';
import { motion, AnimatePresence } from 'framer-motion';
import { FileImage, X } from 'lucide-react';
import { uploadImage } from '@/lib/api';
import { DragDropZone } from '@/components/ui/DragDropZone';
import { Button } from '@/components/ui/button';
import type { SearchResult } from '@/lib/types';

type Props = { onResult: (r: SearchResult[] | string) => void; setLoading: (v: boolean) => void };

export function UploadTab({ onResult, setLoading }: Props) {
  const { mutate } = useSWRConfig();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    return () => { if (preview) URL.revokeObjectURL(preview); };
  }, [preview]);

  function handleFile(f: File) {
    setError('');
    setFile(f);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(f));
  }

  function clearFile() {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setError('');
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const result = await uploadImage(file);
      onResult(result.message);
      mutate('images');
      clearFile();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleUpload} className="space-y-4 max-w-lg">
      <DragDropZone
        accept="image/jpeg,image/png"
        maxSizeMB={10}
        onFile={handleFile}
        onError={setError}
        label="Drop your image here to upload"
        hint="JPEG or PNG, up to 10 MB — or click to browse"
      />

      <AnimatePresence>
        {preview && file && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="flex items-center gap-4 p-3 rounded-xl border border-white/[0.08] bg-card"
          >
            <div className="relative h-16 w-16 rounded-lg overflow-hidden flex-shrink-0 bg-muted">
              <Image src={preview} alt="Preview" fill className="object-cover" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate flex items-center gap-1.5">
                <FileImage className="size-4 text-muted-foreground flex-shrink-0" />
                {file.name}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {(file.size / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
            <button
              type="button"
              onClick={clearFile}
              className="p-1 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="size-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-destructive">
          {error}
        </motion.p>
      )}

      <Button type="submit" disabled={!file} className="w-full sm:w-auto">
        Upload Image
      </Button>
    </form>
  );
}
