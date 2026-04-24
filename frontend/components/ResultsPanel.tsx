import Image from 'next/image';
import type { SelectedImage } from '@/lib/types';

type Props = {
  result: string[] | string | null;
  isLoading: boolean;
  onSelect?: (image: SelectedImage) => void;
};

export function ResultsPanel({ result, isLoading, onSelect }: Props) {
  if (!isLoading && result === null) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-sm font-medium text-gray-700 mb-4">Results</h3>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <div className="h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          Processing…
        </div>
      )}

      {!isLoading && typeof result === 'string' && (
        <p className="text-sm text-gray-700">{result}</p>
      )}

      {!isLoading && Array.isArray(result) && result.length === 0 && (
        <p className="text-sm text-gray-500">No matching images found.</p>
      )}

      {!isLoading && Array.isArray(result) && result.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-3">
            {result.length} image{result.length !== 1 ? 's' : ''} found
            {onSelect && <span className="ml-1">— click Manage to edit tags or delete</span>}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {result.map((url) => (
              <ImageCard
                key={url}
                url={url}
                onSelect={onSelect ? () => onSelect({ url, tags: [] }) : undefined}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ImageCard({ url, onSelect }: { url: string; onSelect?: () => void }) {
  return (
    <div className="group rounded-lg overflow-hidden border border-gray-200 hover:border-blue-400 transition-colors">
      <a href={url} target="_blank" rel="noopener noreferrer" className="block">
        <div className="relative aspect-square bg-gray-100">
          <Image
            src={url}
            alt="Search result"
            fill
            className="object-cover group-hover:opacity-90 transition-opacity"
            sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, 25vw"
          />
        </div>
      </a>
      <div className="flex items-center justify-between px-2 py-1">
        <p className="text-xs text-gray-400 truncate flex-1">{url.split('/').pop()}</p>
        {onSelect && (
          <button
            onClick={onSelect}
            className="text-xs text-blue-600 hover:underline ml-2 flex-shrink-0"
          >
            Manage
          </button>
        )}
      </div>
    </div>
  );
}
