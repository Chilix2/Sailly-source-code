'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface LoginError {
  field?: string;
  message: string;
}

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<LoginError | null>(null);
  const [isLocked, setIsLocked] = useState(false);

  const validateForm = (): boolean => {
    if (!username.trim()) {
      setError({ field: 'username', message: 'Username is required' });
      return false;
    }
    if (!password) {
      setError({ field: 'password', message: 'Password is required' });
      return false;
    }
    if (password.length < 8) {
      setError({ field: 'password', message: 'Password must be at least 8 characters' });
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsLocked(false);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password, rememberMe }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 429) {
          setIsLocked(true);
          setError({
            message: 'Account locked due to too many failed login attempts. Please try again in 15 minutes.',
          });
        } else {
          setError({
            message: data.message || 'Invalid username or password',
          });
        }
        return;
      }

      router.push('/overview');
    } catch (err) {
      setError({
        message: 'Network error. Please check your connection and try again.',
      });
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-surface to-background flex items-center justify-center px-4 py-12">
      {/* Animated grid background */}
      <div className="fixed inset-0 pointer-events-none">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'linear-gradient(rgba(0, 150, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 150, 255, 0.03) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
      </div>

      <div className="w-full max-w-md z-10">
        {/* Logo / Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-text mb-2">Sailly Dashboard</h1>
          <p className="text-text-secondary">Admin authentication required</p>
        </div>

        {/* Login Card */}
        <div className="bg-surface border border-border rounded-lg shadow-2xl p-8 backdrop-blur-sm">
          {/* Error Alert */}
          {error && (
            <div
              className={`mb-6 p-4 rounded-lg border ${
                isLocked
                  ? 'bg-red-900/20 border-red-500/50 text-red-200'
                  : 'bg-orange-900/20 border-orange-500/50 text-orange-200'
              }`}
            >
              <p className="text-sm font-medium">{error.message}</p>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Username Field */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-text mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                disabled={loading || isLocked}
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  setError(null);
                }}
                className={`w-full px-4 py-3 rounded-lg border transition-colors ${
                  error?.field === 'username'
                    ? 'border-red-500/50 focus:border-red-500 bg-red-900/10'
                    : 'border-border focus:border-border-glow bg-surface2'
                } text-text placeholder-text-secondary focus:outline-none focus:ring-2 focus:ring-border-glow/50 disabled:opacity-50 disabled:cursor-not-allowed`}
                placeholder="admin"
              />
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-text mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                disabled={loading || isLocked}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError(null);
                }}
                className={`w-full px-4 py-3 rounded-lg border transition-colors ${
                  error?.field === 'password'
                    ? 'border-red-500/50 focus:border-red-500 bg-red-900/10'
                    : 'border-border focus:border-border-glow bg-surface2'
                } text-text placeholder-text-secondary focus:outline-none focus:ring-2 focus:ring-border-glow/50 disabled:opacity-50 disabled:cursor-not-allowed`}
                placeholder="••••••••"
              />
            </div>

            {/* Stay logged in */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={loading || isLocked}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary/50 accent-primary"
              />
              <span className="text-sm text-white">
                Stay logged in
              </span>
            </label>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || isLocked}
              className="w-full py-3 px-4 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {loading ? 'Signing in...' : isLocked ? 'Account Locked' : 'Sign In'}
            </button>
          </form>

          {/* Security Notice */}
          <div className="mt-6 pt-6 border-t border-border/50">
            <p className="text-xs text-text-secondary text-center">
              This system is protected by industry-standard security measures including Argon2id password hashing,
              HTTPS encryption, and brute-force protection.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8">
          <p className="text-sm text-text-secondary">
            © {new Date().getFullYear()} Sailly. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
}
