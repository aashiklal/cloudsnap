import type { UploadResult, TagInput } from '@/lib/types';
import { getAuthToken, clearTokenCache } from '@/lib/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

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

  let res = await makeRequest(token);

  // On 401, clear the cache and retry once with a fresh token
  if (res.status === 401) {
    clearTokenCache();
    const freshToken = await getAuthToken();
    res = await makeRequest(freshToken);
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

export async function searchByTags(tags: TagInput[]): Promise<string[]> {
  const params = new URLSearchParams();
  tags.forEach((t, i) => {
    params.append(`tag${i + 1}`, t.name);
    params.append(`tag${i + 1}count`, t.count);
  });
  return request<string[]>(`/search?${params.toString()}`, { method: 'GET' });
}

export async function searchByImage(file: File): Promise<string[]> {
  const form = new FormData();
  form.append('file', file, file.name);
  return request<string[]>('/search-by-image', {
    method: 'POST',
    body: form,
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
