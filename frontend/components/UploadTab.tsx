'use client';

import { useState } from 'react';
import Image from 'next/image';
import { uploadImage } from '@/lib/api';

type Props = { onResult: (r: string[] | string) => void; setLoading: (v: boolean) => void };

const MAX_SIZE = 10 * 1024 * 1024;
const ACCEPTED = 'image/jpeg,image/png,image/gif,image/webp';

export function UploadTab({ onResult, setLoading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState('');

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > MAX_SIZE) { setError('File exceeds 10 MB limit'); return; }
    setError('');
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const result = await uploadImage(file);
      onResult(result.url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleUpload} className="space-y-4 max-w-md">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Select image</label>
        <input
          type="file"
          accept={ACCEPTED}
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
        <p className="text-xs text-gray-400 mt-1">JPEG, PNG, GIF, WebP up to 10 MB</p>
      </div>

      {preview && (
        <div className="relative w-48 h-48 rounded-lg overflow-hidden border border-gray-200">
          <Image src={preview} alt="Preview" fill className="object-cover" />
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={!file}
        className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Upload
      </button>
    </form>
  );
}
