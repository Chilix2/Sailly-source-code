'use client';

import { usePathname } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { SessionWarning } from './SessionWarning';

const AUTH_PATHS = ['/login'];

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = AUTH_PATHS.includes(pathname);

  if (isAuthPage) {
    return <main className="min-h-screen">{children}</main>;
  }

  return (
    <>
      <Sidebar />
      <main className="md:ml-64 transition-all duration-300 relative z-0">
        {children}
      </main>
      <SessionWarning />
    </>
  );
}
