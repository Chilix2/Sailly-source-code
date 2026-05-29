'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

function getSessionExpiry(): number | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/session_expires=(\d+)/);
  return match ? parseInt(match[1], 10) : null;
}

export function SessionWarning() {
  const router = useRouter();
  const [minutesLeft, setMinutesLeft] = useState<number | null>(null);
  const [showWarning, setShowWarning] = useState(false);

  const check = useCallback(() => {
    const exp = getSessionExpiry();
    if (!exp) { setShowWarning(false); return; }
    const secsLeft = exp - Math.floor(Date.now() / 1000);
    const mins = Math.ceil(secsLeft / 60);
    setMinutesLeft(mins);
    // Show warning when 5 minutes or less remain
    setShowWarning(secsLeft > 0 && secsLeft <= 300);
    // Auto-redirect if expired
    if (secsLeft <= 0) {
      router.push('/login');
    }
  }, [router]);

  useEffect(() => {
    check();
    const iv = setInterval(check, 10_000);
    return () => clearInterval(iv);
  }, [check]);

  if (!showWarning || minutesLeft == null) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] max-w-sm bg-white border border-amber-300 shadow-xl rounded-xl p-4 animate-in fade-in">
      <div className="flex items-start gap-3">
        <span className="text-2xl">⏰</span>
        <div className="flex-1">
          <p className="text-sm font-semibold text-amber-800">
            Session expires in {minutesLeft} min
          </p>
          <p className="text-xs text-amber-600 mt-0.5">
            You will be logged out automatically. Save your work.
          </p>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => {
                fetch('/api/auth/login', { method: 'HEAD', credentials: 'include' })
                  .catch(() => {});
                setShowWarning(false);
              }}
              className="text-xs px-3 py-1.5 bg-amber-100 hover:bg-amber-200 text-amber-800 rounded-lg font-medium transition"
            >
              Dismiss
            </button>
            <button
              onClick={() => router.push('/login')}
              className="text-xs px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg font-medium transition"
            >
              Re-login now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
