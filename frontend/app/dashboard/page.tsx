'use client';

import { useState } from 'react';
import type { TabId, SelectedImage } from '@/lib/types';
import { UploadTab } from '@/components/UploadTab';
import { GalleryTab } from '@/components/GalleryTab';
import { SearchTagsTab } from '@/components/SearchTagsTab';
import { ReverseSearchTab } from '@/components/ReverseSearchTab';
import { ModifyTagsTab } from '@/components/ModifyTagsTab';
import { DeleteTab } from '@/components/DeleteTab';
import { ResultsPanel } from '@/components/ResultsPanel';

const TABS: { id: TabId; label: string }[] = [
  { id: 'upload', label: 'Upload' },
  { id: 'gallery', label: 'My Images' },
  { id: 'search', label: 'Search by Tags' },
  { id: 'reverse', label: 'Search by Image' },
  { id: 'modify', label: 'Edit Tags' },
  { id: 'delete', label: 'Delete' },
];

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabId>('upload');
  const [result, setResult] = useState<string[] | string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<SelectedImage | null>(null);

  function navigate(tab: TabId, image?: SelectedImage) {
    setActiveTab(tab);
    setResult(null);
    if (image !== undefined) setSelectedImage(image);
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Image Management</h2>
        <p className="text-sm text-gray-500 mt-1">Upload, search, and manage your images</p>
      </div>

      <div className="border-b border-gray-200">
        <nav className="flex gap-1 flex-wrap" aria-label="Tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => navigate(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-white border border-b-white border-gray-200 text-blue-600 -mb-px'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {activeTab === 'upload' && (
          <UploadTab onResult={setResult} setLoading={setIsLoading} />
        )}
        {activeTab === 'gallery' && (
          <GalleryTab
            onManage={(img, action) => navigate(action === 'modify' ? 'modify' : 'delete', img)}
          />
        )}
        {activeTab === 'search' && (
          <SearchTagsTab onResult={setResult} setLoading={setIsLoading} />
        )}
        {activeTab === 'reverse' && (
          <ReverseSearchTab onResult={setResult} setLoading={setIsLoading} />
        )}
        {activeTab === 'modify' && (
          <ModifyTagsTab
            onResult={setResult}
            setLoading={setIsLoading}
            selectedImage={selectedImage ?? undefined}
            onClearSelection={() => setSelectedImage(null)}
          />
        )}
        {activeTab === 'delete' && (
          <DeleteTab
            onResult={setResult}
            setLoading={setIsLoading}
            selectedImage={selectedImage ?? undefined}
            onClearSelection={() => setSelectedImage(null)}
          />
        )}
      </div>

      <ResultsPanel
        result={result}
        isLoading={isLoading}
        onSelect={(img) => navigate('modify', img)}
      />
    </div>
  );
}
