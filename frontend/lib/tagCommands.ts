import type { TagInput } from '@/lib/types';

export type TagMutationType = '0' | '1';

export function toSearchTagCommand(tags: TagInput[]): URLSearchParams {
  const params = new URLSearchParams();

  tags.forEach((tag, index) => {
    const position = index + 1;
    params.append(`tag${position}`, tag.name);
    params.append(`tag${position}count`, tag.count);
  });

  return params;
}

export function toModifyTagCommand(
  url: string,
  type: TagMutationType,
  tags: TagInput[]
): Record<string, string | number> {
  const body: Record<string, string | number> = { url, type };

  tags.forEach((tag, index) => {
    const position = index + 1;
    body[`tag${position}`] = tag.name;
    body[`tag${position}count`] = parseInt(tag.count, 10);
  });

  return body;
}
