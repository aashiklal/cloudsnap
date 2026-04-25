import type { UploadResult, TagInput, SearchResult } from '@/lib/types';
import { getAuthToken, clearTokenCache } from '@/lib/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;
if (!API_BASE) throw new Error('NEXT_PUBLIC_API_URL is not configured');

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const token = await getAuthToken();

  const makeRequest = (t: string) =>
    fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${t}`,
        ...(options.headers ?? {}),
      },
    });

  let res: Response;
  try {
    res = await makeRequest(token);
  } catch {
    throw new Error('Cannot reach the API — check your network or CORS configuration.');
  }

  // On 401, clear the cache and retry once with a fresh token
  if (res.status === 401) {
    clearTokenCache();
    const freshToken = await getAuthToken();
    try {
      res = await makeRequest(freshToken);
    } catch {
      throw new Error('Cannot reach the API — check your network or CORS configuration.');
    }
  }

  const data = await res.json();
  if (!res.ok) throw new Error(data?.error ?? `Request failed: ${res.status}`);
  return data as T;
}

export async function uploadImage(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('filename', file.name);

  // FormData must not have Content-Type set manually (browser sets boundary automatically)
  return request<UploadResult>('/upload', {
    method: 'POST',
    body: form,
  });
}

export async function searchByTags(tags: TagInput[]): Promise<SearchResult[]> {
  const params = new URLSearchParams();
  tags.forEach((t, i) => {
    params.append(`tag${i + 1}`, t.name);
    params.append(`tag${i + 1}count`, t.count);
  });
  return request<SearchResult[]>(`/search?${params.toString()}`, { method: 'GET' });
}

// Lambda payload limit is 6 MB; base64 adds ~33% overhead, so cap raw bytes at 3.5 MB.
// Rekognition label detection works fine on downscaled images.
const SEARCH_IMAGE_MAX_BYTES = 3.5 * 1024 * 1024;
const SEARCH_IMAGE_MAX_DIM = 1920;

async function resizeAndEncodeImage(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file);
  let { width, height } = bitmap;

  if (width > SEARCH_IMAGE_MAX_DIM || height > SEARCH_IMAGE_MAX_DIM) {
    if (width >= height) {
      height = Math.round((height * SEARCH_IMAGE_MAX_DIM) / width);
      width = SEARCH_IMAGE_MAX_DIM;
    } else {
      width = Math.round((width * SEARCH_IMAGE_MAX_DIM) / height);
      height = SEARCH_IMAGE_MAX_DIM;
    }
  }

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  for (const quality of [0.85, 0.7, 0.55, 0.4]) {
    const dataUrl = canvas.toDataURL('image/jpeg', quality);
    const b64 = dataUrl.split(',')[1];
    if (b64.length * 0.75 <= SEARCH_IMAGE_MAX_BYTES) return b64;
  }
  return canvas.toDataURL('image/jpeg', 0.4).split(',')[1];
}

export async function searchByImage(file: File): Promise<SearchResult[]> {
  const imageFile = await resizeAndEncodeImage(file);
  return request<SearchResult[]>('/search-by-image', {
    method: 'POST',
    body: JSON.stringify({ imageFile }),
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function modifyTags(
  url: string,
  type: '0' | '1',
  tags: TagInput[]
): Promise<{ message: string }> {
  const body: Record<string, string | number> = { url, type };
  tags.forEach((t, i) => {
    body[`tag${i + 1}`] = t.name;
    body[`tag${i + 1}count`] = parseInt(t.count, 10);
  });
  return request<{ message: string }>('/modify-tags', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function listImages(): Promise<import('./types').ImageRecord[]> {
  return request<import('./types').ImageRecord[]>('/images', { method: 'GET' });
}

export async function deleteImage(imageUrl: string): Promise<{ message: string }> {
  const params = new URLSearchParams({ image_url: imageUrl });
  return request<{ message: string }>(`/delete?${params.toString()}`, { method: 'DELETE' });
}
