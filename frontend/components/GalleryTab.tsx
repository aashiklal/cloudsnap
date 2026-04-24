'use client';

import Image from 'next/image';
import useSWR from 'swr';
import { listImages } from '@/lib/api';
import type { ImageRecord, SelectedImage } from '@/lib/types';

type Props = {
  onManage: (image: SelectedImage, action: 'modify' | 'delete') => void;
};

export function GalleryTab({ onManage }: Props) {
  const { data: images, error, isLoading, mutate } = useSWR(
    'images',
    () => listImages(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30_000, // cache for 30 seconds
    }
  );

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <div className="h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        Loading images…
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-red-600">{error instanceof Error ? error.message : 'Failed to load images'}</p>
        <button
          onClick={() => mutate()}
          className="text-sm text-blue-600 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!images || images.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-sm">No images yet. Upload one to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">{images.length} image{images.length !== 1 ? 's' : ''}</p>
        <button
          onClick={() => mutate()}
          className="text-xs text-blue-600 hover:underline"
        >
          Refresh
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {images.map((img) => (
          <GalleryCard key={img.ImageURL} image={img} onManage={onManage} />
        ))}
      </div>
    </div>
  );
}

function GalleryCard({
  image,
  onManage,
}: {
  image: ImageRecord;
  onManage: (image: SelectedImage, action: 'modify' | 'delete') => void;
}) {
  const filename = image.ImageURL.split('/').pop() ?? image.ImageURL;
  const selected: SelectedImage = { url: image.ImageURL, tags: image.Tags };

  return (
    <div className="group relative rounded-lg overflow-hidden border border-gray-200 bg-white hover:border-blue-400 transition-colors">
      <div className="relative aspect-square bg-gray-100">
        <Image
          src={image.ImageURL}
          alt={filename}
          fill
          className="object-cover"
          sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, 25vw"
        />
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <button
            onClick={() => onManage(selected, 'modify')}
            className="bg-white text-gray-800 text-xs font-medium px-3 py-1.5 rounded-md hover:bg-blue-50 hover:text-blue-700 transition-colors"
          >
            Edit Tags
          </button>
          <button
            onClick={() => onManage(selected, 'delete')}
            className="bg-white text-red-600 text-xs font-medium px-3 py-1.5 rounded-md hover:bg-red-50 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
      <div className="p-2">
        <p className="text-xs text-gray-600 truncate font-medium">{filename}</p>
        {image.Tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {image.Tags.slice(0, 3).map((t) => (
              <span key={t.tag} className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">
                {t.tag}
              </span>
            ))}
            {image.Tags.length > 3 && (
              <span className="text-xs text-gray-400">+{image.Tags.length - 3}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
