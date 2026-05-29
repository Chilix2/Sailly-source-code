'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
export default function Home() {
    const router = useRouter();
    useEffect(() => {
        router.push('/overview');
    }, [router]);
    return (<div className="min-h-screen bg-background flex items-center justify-center">
      <p className="text-text-muted">Redirecting to Command Center...</p>
    </div>);
}
