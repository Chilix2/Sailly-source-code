'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.push('/overview');
  }, [router]);

  return (
    <div className="min-h-screen bg-transparent flex items-center justify-center">
      <p className="text-black">Redirecting...</p>
    </div>
  );
}
