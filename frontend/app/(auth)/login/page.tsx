'use client';

import { useEffect, useState } from 'react';
import { fetchAuthSession, signIn } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Cloud, Mail, Lock, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

const FEATURES = [
  'Upload & auto-tag with AWS Rekognition',
  'Search images by tags or visual similarity',
  'Manage your entire image library',
];

const inputClass = 'w-full pl-9 pr-3 py-2.5 border border-white/[0.09] rounded-lg text-sm bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/25 focus:border-primary transition-colors';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAuthSession()
      .then((s) => { if (s.tokens) router.replace('/dashboard'); })
      .catch(() => {});
  }, [router]);

  const ERROR_MESSAGES: Record<string, string> = {
    NotAuthorizedException: 'Incorrect email or password.',
    UserNotFoundException: 'No account found with that email.',
    UserNotConfirmedException: 'Please confirm your email first.',
    UserAlreadyAuthenticatedException: 'Already signed in.',
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await signIn({ username: email, password });
      router.push('/dashboard');
    } catch (err: unknown) {
      const name = (err as { name?: string }).name ?? '';
      if (name === 'UserAlreadyAuthenticatedException') {
        router.replace('/dashboard');
        return;
      }
      setError(ERROR_MESSAGES[name] ?? (err instanceof Error ? err.message : 'Sign in failed'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left: brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 relative overflow-hidden mesh-bg">
        {/* Decorative ring */}
        <div
          className="absolute -top-32 -left-32 w-96 h-96 rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, oklch(0.62 0.19 215 / 0.18) 0%, transparent 70%)' }}
        />
        <div
          className="absolute -bottom-24 -right-24 w-80 h-80 rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, oklch(0.52 0.22 230 / 0.14) 0%, transparent 70%)' }}
        />

        <div className="flex items-center gap-2.5 relative">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl brand-gradient"
            style={{ boxShadow: '0 0 20px var(--primary-glow)' }}
          >
            <Cloud className="size-5 text-white" />
          </div>
          <span className="text-xl font-semibold text-white tracking-tight">CloudSnap</span>
        </div>

        <div className="space-y-8 relative">
          <div>
            <h2
              className="leading-[1.15] font-extrabold brand-gradient-text"
              style={{ fontSize: 'clamp(2rem, 3.5vw, 2.75rem)' }}
            >
              AI-powered image management on AWS
            </h2>
            <p className="mt-3 text-base" style={{ color: 'oklch(0.96 0.005 264 / 0.55)' }}>
              Upload once, search forever. Let Rekognition do the tagging.
            </p>
          </div>
          <ul className="space-y-3.5">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-3 text-sm" style={{ color: 'oklch(0.96 0.005 264 / 0.75)' }}>
                <CheckCircle2 className="size-4 text-primary flex-shrink-0" />
                {f}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs relative" style={{ color: 'oklch(0.96 0.005 264 / 0.3)' }}>
          Powered by AWS S3 · Rekognition · DynamoDB · Cognito
        </p>
      </div>

      {/* Right: form panel */}
      <div className="flex items-center justify-center p-8 bg-background">
        {/* Mobile brand header */}
        <div className="absolute top-6 left-6 flex items-center gap-2 lg:hidden">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg brand-gradient">
            <Cloud className="size-4 text-white" />
          </div>
          <span className="text-base font-semibold text-foreground">CloudSnap</span>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="w-full max-w-sm"
        >
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-foreground">
              <span className="brand-gradient-text">Sign</span> in
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Welcome back to CloudSnap</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium text-foreground">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium text-foreground">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            {error && (
              <motion.p
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="text-sm text-destructive"
              >
                {error}
              </motion.p>
            )}

            <Button type="submit" disabled={loading} className="w-full mt-2 h-10 text-sm font-semibold">
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            No account?{' '}
            <Link href="/signup" className="text-primary hover:underline font-medium">
              Create one
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
