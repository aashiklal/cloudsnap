'use client';

import { fetchAuthSession, signOut } from 'aws-amplify/auth';

interface CachedToken {
  value: string;
  expiresAt: number;
}

// Refresh 3 minutes before expiry to avoid 401s on in-flight requests
const REFRESH_BUFFER_MS = 3 * 60 * 1000;

let tokenCache: CachedToken | null = null;

export async function getAuthToken(): Promise<string> {
  const now = Date.now();
  if (tokenCache && now < tokenCache.expiresAt - REFRESH_BUFFER_MS) {
    return tokenCache.value;
  }

  const session = await fetchAuthSession({ forceRefresh: tokenCache !== null });
  const idToken = session.tokens?.idToken;
  if (!idToken) throw new Error('No auth token — please sign in');

  const token = idToken.toString();
  let payload: { exp: number };
  try {
    payload = JSON.parse(atob(token.split('.')[1]));
  } catch {
    tokenCache = null;
    throw new Error('Auth session is corrupted — please sign in again');
  }
  const expiresAt = (payload.exp as number) * 1000;

  tokenCache = { value: token, expiresAt };
  return token;
}

export function clearTokenCache(): void {
  tokenCache = null;
}

export async function handleSignOut(): Promise<void> {
  clearTokenCache();
  await signOut();
}
