export interface Tag {
  tag: string;
  count: number;
}

export interface ImageRecord {
  ImageURL: string;
  Tags: Tag[];
}

export type TabId = 'upload' | 'gallery' | 'search' | 'reverse' | 'modify' | 'delete';

export type SelectedImage = {
  url: string;
  tags: Tag[];
};

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
