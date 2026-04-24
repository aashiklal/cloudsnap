import type { UploadResult, TagInput } from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

async function request<T>(path: string, options: RequestInit, token: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error ?? `Request failed: ${res.status}`);
  return data as T;
}

export async function uploadImage(base64: string, filename: string, token: string): Promise<UploadResult> {
  return request<UploadResult>('/upload', {
    method: 'POST',
    body: JSON.stringify({ image: base64, filename }),
  }, token);
}

export async function searchByTags(tags: TagInput[], token: string): Promise<string[]> {
  const params = new URLSearchParams();
  tags.forEach((t, i) => {
    params.append(`tag${i + 1}`, t.name);
    params.append(`tag${i + 1}count`, t.count);
  });
  const res = await fetch(`${API_BASE}/search?${params.toString()}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error ?? `Search failed: ${res.status}`);
  return data as string[];
}

export async function searchByImage(base64: string, token: string): Promise<string[]> {
  return request<string[]>('/search-by-image', {
    method: 'POST',
    body: JSON.stringify({ imageFile: base64 }),
  }, token);
}

export async function modifyTags(
  url: string,
  type: '0' | '1',
  tags: TagInput[],
  token: string
): Promise<{ message: string }> {
  const body: Record<string, string | number> = { url, type };
  tags.forEach((t, i) => {
    body[`tag${i + 1}`] = t.name;
    body[`tag${i + 1}count`] = parseInt(t.count, 10);
  });
  return request<{ message: string }>('/modify-tags', {
    method: 'POST',
    body: JSON.stringify(body),
  }, token);
}

export async function listImages(token: string): Promise<import('./types').ImageRecord[]> {
  const res = await fetch(`${API_BASE}/images`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error ?? `Request failed: ${res.status}`);
  return data as import('./types').ImageRecord[];
}

export async function deleteImage(imageUrl: string, token: string): Promise<{ message: string }> {
  const params = new URLSearchParams({ image_url: imageUrl });
  const res = await fetch(`${API_BASE}/delete?${params.toString()}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error ?? `Delete failed: ${res.status}`);
  return data as { message: string };
}
