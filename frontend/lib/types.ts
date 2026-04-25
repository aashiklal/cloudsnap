export interface Tag {
  tag: string;
  count: number;
}

export interface ImageRecord {
  ImageURL: string;
  PresignedURL?: string;
  Tags: Tag[];
  UserID?: string;
  UploadedAt?: string;
}

export type TabId = 'upload' | 'gallery' | 'search' | 'reverse' | 'modify';

export type SelectedImage = {
  url: string;
  presignedUrl?: string;
  tags: Tag[];
};

export interface SearchResult {
  imageUrl: string;
  presignedUrl: string;
}

export interface ApiError {
  error: string;
}

export interface UploadResult {
  message: string;
  url: string;
}

export interface TagInput {
  name: string;
  count: string;
}
