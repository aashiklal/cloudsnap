'use client';

import { useState } from 'react';
import Image from 'next/image';
import { getAuthToken } from '@/lib/auth';
import { deleteImage } from '@/lib/api';
import type { SelectedImage } from '@/lib/types';

type Props = {
  onResult: (r: string[] | string) => void;
  setLoading: (v: boolean) => void;
  selectedImage?: SelectedImage;
  onClearSelection?: () => void;
};

export function DeleteTab({ onResult, setLoading, selectedImage, onClearSelection }: Props) {
  const [manualUrl, setManualUrl] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');

  const imageUrl = selectedImage?.url ?? manualUrl;

  async function handleDelete() {
    setLoading(true);
    setError('');
    setConfirming(false);
    try {
      const token = await getAuthToken();
      const result = await deleteImage(imageUrl, token);
      onResult(result.message);
      setManualUrl('');
      onClearSelection?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 max-w-md">
      {selectedImage ? (
        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <div className="relative h-16 w-16 flex-shrink-0 rounded overflow-hidden bg-gray-200">
            <Image src={selectedImage.url} alt="Selected" fill className="object-cover" sizes="64px" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-700 truncate">
              {selectedImage.url.split('/').pop()}
            </p>
          </div>
          {onClearSelection && (
            <button
              type="button"
              onClick={onClearSelection}
              className="text-xs text-gray-400 hover:text-gray-600 flex-shrink-0"
            >
              Change
            </button>
          )}
        </div>
      ) : (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Image URL</label>
          <input
            type="url"
            value={manualUrl}
            onChange={(e) => setManualUrl(e.target.value)}
            placeholder="https://your-bucket.s3.amazonaws.com/photo.jpg"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!confirming ? (
        <button
          type="button"
          disabled={!imageUrl.trim()}
          onClick={() => setConfirming(true)}
          className="bg-red-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Delete image
        </button>
      ) : (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-3">
          <p className="text-sm font-medium text-red-800">
            This will permanently delete the image from S3 and the database. Are you sure?
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleDelete}
              className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
            >
              Yes, delete
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="bg-white text-gray-700 border border-gray-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
