'use client';

/**
 * Fix validation loop UI: bucket Step 1 (10) + Step 2 (10), Tier 1/2 thresholds.
 * Static files are served from /tmp/ab_fix_validation/iter_N/ on the host; nginx
 * proxies https://sailly.tech/fix-validation/ → port 8767.
 */
export default function FixValidationPage() {
  return (
    <div className="flex flex-col h-screen">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#f5e9e4] bg-white">
        <div>
          <h1 className="text-xl font-bold text-brand-navy">Fix validation loop</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Bucket validation (10+10 scenarios, up to 3 retries per bucket) — separate from the 280-scenario
            training loop. Open the highest <code className="text-xs bg-[#f5e9e4] px-1 rounded">iter_*</code>{' '}
            folder, then <code className="text-xs bg-[#f5e9e4] px-1 rounded">index.html</code>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="/fix-validation/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded-lg border border-[#e8d8d2] text-brand-navy hover:text-brand-pink hover:border-brand-pink transition-colors font-medium"
          >
            Directory listing ↗
          </a>
        </div>
      </div>

      <iframe
        src="/fix-validation/"
        className="flex-1 w-full border-0"
        title="Fix validation — iteration folders"
        allow="same-origin"
      />
    </div>
  );
}
