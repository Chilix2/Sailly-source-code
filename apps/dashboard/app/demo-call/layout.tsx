import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Demo Call — Sailly KI Sprachagent',
  description: 'Testen Sie den KI-Sprachagenten live im Browser. Bestellen, reservieren, oder Fragen stellen.',
};

export default function DemoCallLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
