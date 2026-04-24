'use client';

import { useState } from 'react';
import { getAuthToken } from '@/lib/auth';
import { searchByImage } from '@/lib/api';

type Props = { onResult: (r: string[] | string) => void; setLoading: (v: boolean) => void };

const MAX_SIZE = 10 * 1024 * 1024;

export function ReverseSearchTab({ onResult, setLoading }: Props) {
  const [error, setError] = useState('');

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_SIZE) { setError('File exceeds 10 MB limit'); return; }
    setError('');
    setLoading(true);
    try {
      const token = await getAuthToken();
      const base64 = await fileToBase64(file);
      const results = await searchByImage(base64, token);
      onResult(results);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 max-w-md">
      <p className="text-sm text-gray-600">
        Upload an image to find visually similar images in your library based on detected objects.
      </p>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Query image</label>
        <input
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          onChange={handleChange}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
        <p className="text-xs text-gray-400 mt-1">Select an image to search automatically</p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}

async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
