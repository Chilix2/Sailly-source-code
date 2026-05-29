'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  Phone,
  History,
  Settings,
  LineChart,
  Zap,
  DollarSign,
  Lock,
  Menu,
  X,
  ChevronRight,
  ShieldCheck,
  MessageSquare,
  Star,
  Mic,
  FlaskConical,
  LogOut,
  Activity,
  GitBranch,
  PlusCircle,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const navigationGroups = [
  {
    label: 'Operations',
    items: [
      { label: 'Overview', href: '/overview', icon: BarChart3 },
      { label: 'Live Calls', href: '/live-calls', icon: Phone, badge: '0' },
      { label: 'Demo Call', href: '/demo-call', icon: Mic },
      { label: 'Call History', href: '/calls', icon: History },
      { label: 'Call Analysis', href: '/call-analysis', icon: Activity },
      { label: 'Checkpoints', href: '/checkpoints', icon: ShieldCheck },
      { label: 'Validation Runs', href: '/crucial-fix', icon: FlaskConical },
    ],
  },
  {
    label: 'Configure',
    items: [
      { label: 'Agent Config', href: '/agent', icon: Settings },
      { label: 'Testing', href: '/testing', icon: Zap },
      { label: 'Debugger', href: '/builder', icon: GitBranch },
      { label: 'New Agent', href: '/tenants/new', icon: PlusCircle },
    ],
  },
  {
    label: 'Insights',
    items: [
      { label: 'Conversations', href: '/conversations', icon: MessageSquare },
      { label: 'Analytics', href: '/analytics', icon: LineChart },
      { label: 'Quality', href: '/quality', icon: Star },
      { label: 'Cost Center', href: '/costs', icon: DollarSign },
    ],
  },
  {
    label: 'Data',
    items: [
      { label: 'Compliance', href: '/compliance', icon: Lock },
      { label: 'GDPR', href: '/gdpr', icon: Lock },
    ],
  },
  {
    label: 'Legacy',
    items: [
      { label: 'Pipeline', href: '/pipeline', icon: Zap },
      { label: 'Restaurants', href: '/restaurants', icon: Menu },
      { label: 'Webhooks', href: '/webhooks', icon: ChevronRight },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const validationRunning = false;
  const validationPhase = '';

  const handleLogout = async () => {
    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (response.ok) {
        // Clear any client-side session data
        document.cookie = 'session_expires=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
        router.push('/login');
      }
    } catch (error) {
      console.error('Logout failed:', error);
      // Force redirect even if API fails
      router.push('/login');
    }
  };

  // Don't show sidebar on login page
  if (pathname === '/login') return null;

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed md:hidden bottom-4 right-4 z-50 p-2 bg-white shadow-sm border border-brand-cream rounded-lg"
      >
        {isOpen ? <X size={20} fill="currentColor" /> : <Menu size={20} fill="currentColor" />}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-screen w-64 bg-[#f5e9e4]/30 backdrop-blur-md border-r border-[#f5e9e4] shadow-sm flex flex-col z-50 transition-transform duration-300 md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-6 border-b border-brand-cream">
          <h1 className="text-lg font-bold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-pink animate-pulse" />
            <span>
              <span className="text-brand-pink">sailly</span>
              <span className="text-brand-muted">.cmd</span>
            </span>
          </h1>
          <p className="text-xs text-brand-muted mt-2">Command Center</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-6">
          {navigationGroups.map((group) => (
            <div key={group.label} className="bg-white rounded-2xl p-3 shadow-md border border-[#e8d8d2] space-y-1">
              <h3 className="px-3 py-2 text-xs font-bold text-brand-navy uppercase tracking-widest border-b border-[#f5e9e4] mb-2 pb-2">
                {group.label}
              </h3>
              <div className="pt-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href || pathname.startsWith(item.href + '/');

                  const isValidationRuns = item.href === '/crucial-fix';
                  const cfvActive = validationRunning && validationPhase.includes('CFV');
                  const showRunningBadge = isValidationRuns && validationRunning && !cfvActive;
                  const showCfvBadge = isValidationRuns && cfvActive;

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setIsOpen(false)}
                      title={
                        showCfvBadge ? `CFV active: ${validationPhase}`
                        : showRunningBadge ? validationPhase || 'Validation running…'
                        : undefined
                      }
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-bold transition-all duration-200 mb-1 ${
                        isActive
                          ? 'bg-[#fff0f7] text-brand-pink border border-[#ffc2e0]'
                          : 'text-brand-navy hover:text-brand-pink hover:bg-[#fff0f7]'
                      }`}
                    >
                    <Icon size={16} fill="currentColor" />
                    <span className="flex-1">{item.label}</span>
                    {showCfvBadge ? (
                      <span className="flex items-center gap-1.5 px-2 py-0.5 text-xs bg-amber-50 text-amber-700 border border-amber-200 rounded-full font-semibold">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                        Active
                      </span>
                    ) : showRunningBadge ? (
                      <span className="flex items-center gap-1.5 px-2 py-0.5 text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full font-semibold">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        Running
                      </span>
                    ) : item.badge ? (
                      <span className="px-2 py-0.5 text-xs bg-brand-pink text-white rounded-full font-medium">
                        {item.badge}
                      </span>
                    ) : null}
                  </Link>
                );
              })}
              </div>
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-brand-cream text-xs text-brand-muted space-y-3">
          <div className="space-y-1">
            <p className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              Connected
            </p>
            <p>v1.0.0</p>
          </div>
          
          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium text-brand-navy hover:text-brand-pink hover:bg-[#fff0f7] rounded-lg transition-all duration-200 border border-transparent hover:border-[#ffc2e0]"
          >
            <LogOut size={16} />
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 md:hidden z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}

