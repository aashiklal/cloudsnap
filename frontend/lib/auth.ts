'use client';

import { fetchAuthSession, signOut } from 'aws-amplify/auth';

export async function getAuthToken(): Promise<string> {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();
  if (!token) throw new Error('No auth token — please sign in');
  return token;
}

export async function handleSignOut(): Promise<void> {
  await signOut();
}
