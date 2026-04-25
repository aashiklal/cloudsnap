'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Images, Tag, ScanSearch, Tags } from 'lucide-react';
import type { TabId, SelectedImage, SearchResult } from '@/lib/types';
import { UploadTab } from '@/components/UploadTab';
import { GalleryTab } from '@/components/GalleryTab';
import { SearchTagsTab } from '@/components/SearchTagsTab';
import { ReverseSearchTab } from '@/components/ReverseSearchTab';
import { ModifyTagsTab } from '@/components/ModifyTagsTab';
import { ResultsPanel } from '@/components/ResultsPanel';
import { ErrorBoundary } from '@/components/ErrorBoundary';

const TABS: { id: TabId; label: string; shortLabel: string; icon: React.ElementType }[] = [
  { id: 'upload',  label: 'Upload',         shortLabel: 'Upload',   icon: Upload },
  { id: 'gallery', label: 'My Images',       shortLabel: 'Gallery',  icon: Images },
  { id: 'search',  label: 'Search by Tags',  shortLabel: 'Tags',     icon: Tag },
  { id: 'reverse', label: 'Search by Image', shortLabel: 'Reverse',  icon: ScanSearch },
  { id: 'modify',  label: 'Edit Tags',       shortLabel: 'Edit',     icon: Tags },
];

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabId>('upload');
  const [result, setResult] = useState<SearchResult[] | string | null>(null);
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
        <h2 className="text-xl font-semibold tracking-tight">
          <span className="brand-gradient-text">Image Management</span>
        </h2>
        <p className="text-sm text-muted-foreground mt-0.5">Upload, search, and manage your cloud images</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-muted rounded-xl p-1 overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => navigate(tab.id)}
              className="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap z-10 flex-shrink-0"
              style={{ color: isActive ? '#fff' : 'var(--muted-foreground)' }}
            >
              {isActive && (
                <motion.div
                  layoutId="tab-pill"
                  className="absolute inset-0 brand-gradient rounded-lg shadow-sm"
                  style={{ zIndex: -1, boxShadow: '0 0 12px var(--primary-glow)' }}
                  transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                />
              )}
              <Icon className="size-3.5 relative" style={{ opacity: isActive ? 1 : 0.55 }} />
              <span className="relative hidden sm:inline">{tab.label}</span>
              <span className="relative sm:hidden">{tab.shortLabel}</span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <ErrorBoundary>
        <div
          className="bg-card rounded-xl border border-border p-6 min-h-[300px]"
          style={{ boxShadow: 'inset 0 1px 0 oklch(1 0 0 / 0.06), 0 1px 3px oklch(0 0 0 / 0.3)' }}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
            >
              {activeTab === 'upload' && (
                <UploadTab onResult={setResult} setLoading={setIsLoading} />
              )}
              {activeTab === 'gallery' && (
                <GalleryTab onEditTags={(img) => navigate('modify', img)} />
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
                  preselected={selectedImage ?? undefined}
                  onClearPreselected={() => setSelectedImage(null)}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </ErrorBoundary>

      <ResultsPanel
        result={result}
        isLoading={isLoading}
        onSelect={(img) => navigate('modify', img)}
      />
    </div>
  );
}
