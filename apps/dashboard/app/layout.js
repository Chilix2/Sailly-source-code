import './globals.css';
import { LayoutShell } from '@/components/LayoutShell';
export const metadata = {
    title: 'Sailly Command Center — Voice AI Operations',
    description: 'Real-time monitoring and operations dashboard for voice AI',
};
export default function RootLayout({ children, }) {
    return (<html lang="en">
      <body className="bg-background text-text font-sans">
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>);
}
