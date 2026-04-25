'use client';

import { useState } from 'react';
import { signUp, confirmSignUp } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Cloud, Mail, Lock, MailCheck, KeyRound, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

const FEATURES = [
  'Upload & auto-tag with AWS Rekognition',
  'Search images by tags or visual similarity',
  'Manage your entire image library',
];

type Step = 'form' | 'confirm';

const inputWithIcon = 'w-full pl-9 pr-3 py-2.5 border border-white/[0.09] rounded-lg text-sm bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/25 focus:border-primary transition-colors';
const inputPlain = 'w-full px-3 py-2.5 border border-white/[0.09] rounded-lg text-sm bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/25 focus:border-primary transition-colors';

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('form');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSignUp(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await signUp({
        username: email,
        password,
        options: {
          userAttributes: { email, given_name: firstName, family_name: lastName },
        },
      });
      setStep('confirm');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Sign up failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await confirmSignUp({ username: email, confirmationCode: code });
      router.push('/login');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Confirmation failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left: brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 relative overflow-hidden mesh-bg">
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

        <div className="w-full max-w-sm">
          <AnimatePresence mode="wait">
            {step === 'form' ? (
              <motion.div
                key="form"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25 }}
              >
                <div className="mb-8">
                  <h1 className="text-2xl font-bold text-foreground">
                    <span className="brand-gradient-text">Create</span> your account
                  </h1>
                  <p className="text-sm text-muted-foreground mt-1">Join CloudSnap to manage your images</p>
                </div>

                <form onSubmit={handleSignUp} className="space-y-4">
                  <div className="flex gap-3">
                    <div className="flex-1 space-y-1.5">
                      <label className="text-sm font-medium text-foreground">First name</label>
                      <input
                        type="text"
                        required
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        className={inputPlain}
                      />
                    </div>
                    <div className="flex-1 space-y-1.5">
                      <label className="text-sm font-medium text-foreground">Last name</label>
                      <input
                        type="text"
                        required
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        className={inputPlain}
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-foreground">Email</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className={inputWithIcon}
                        placeholder="you@example.com"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-foreground">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
                      <input
                        type="password"
                        required
                        minLength={8}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className={inputWithIcon}
                      />
                    </div>
                  </div>

                  {error && (
                    <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-destructive">
                      {error}
                    </motion.p>
                  )}

                  <Button type="submit" disabled={loading} className="w-full mt-2 h-10 text-sm font-semibold">
                    {loading ? 'Creating account…' : 'Create account'}
                  </Button>
                </form>

                <p className="mt-6 text-center text-sm text-muted-foreground">
                  Already have an account?{' '}
                  <Link href="/login" className="text-primary hover:underline font-medium">
                    Sign in
                  </Link>
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="confirm"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25 }}
              >
                <div className="mb-8 text-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl mx-auto mb-4"
                    style={{ background: 'oklch(0.62 0.19 215 / 0.12)', border: '1px solid oklch(0.62 0.19 215 / 0.2)' }}
                  >
                    <MailCheck className="size-7 text-primary" />
                  </div>
                  <h1 className="text-2xl font-bold text-foreground">Check your email</h1>
                  <p className="text-sm text-muted-foreground mt-1">
                    We sent a confirmation code to{' '}
                    <span className="font-medium text-foreground">{email}</span>
                  </p>
                </div>

                <form onSubmit={handleConfirm} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-foreground">Confirmation code</label>
                    <div className="relative">
                      <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
                      <input
                        type="text"
                        required
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        className={`${inputWithIcon} text-lg tracking-widest font-mono text-center`}
                        placeholder="000000"
                        maxLength={6}
                      />
                    </div>
                  </div>

                  {error && (
                    <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-destructive">
                      {error}
                    </motion.p>
                  )}

                  <Button type="submit" disabled={loading} className="w-full mt-2 h-10 text-sm font-semibold">
                    {loading ? 'Confirming…' : 'Confirm account'}
                  </Button>
                </form>

                <p className="mt-6 text-center text-sm text-muted-foreground">
                  <Link href="/login" className="text-primary hover:underline font-medium">
                    Back to sign in
                  </Link>
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
