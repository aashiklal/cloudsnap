export interface Tag {
  tag: string;
  count: number;
}

export type ProcessingStatus = 'processing' | 'ready' | 'failed';

export interface ImageRecord {
  ImageURL: string;
  PresignedURL?: string;
  Tags: Tag[];
  ProcessingStatus: ProcessingStatus;
  ProcessingError?: string;
  ProcessedAt?: string;
  UserID?: string;
  UploadedAt?: string;
}

export type TabId = 'upload' | 'gallery' | 'search' | 'reverse' | 'modify';

export type SelectedImage = {
  url: string;
  presignedUrl?: string;
  tags: Tag[];
  processingStatus?: ProcessingStatus;
};

export interface SearchResult {
  imageUrl: string;
  presignedUrl: string;
  processingStatus?: ProcessingStatus;
}

export interface ApiError {
  error: string;
}

export interface UploadResult {
  message: string;
  url: string;
  processingStatus: ProcessingStatus;
}

export interface TagInput {
  name: string;
  count: string;
}
