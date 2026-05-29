import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const INDUSTRY_LABELS: Record<string, string> = {
  restaurant: 'Restaurant',
  hotel:      'Hotel',
  medical:    'Praxis / Medizin',
  services:   'Dienstleistungen',
  beauty:     'Beauty & Wellness',
  retail:     'Einzelhandel',
  banking:    'Finanzdienstleistungen',
};

const INDUSTRY_ICONS: Record<string, string> = {
  restaurant: '🍜',
  hotel:      '🏨',
  medical:    '🏥',
  services:   '🔧',
  beauty:     '💅',
  retail:     '🛍️',
  banking:    '🏦',
};

// Fallback tenant list in case we can't read the YAML configs
const FALLBACK_TENANTS = [
  { id: 'doboo',        label: 'DOBOO Korean Soulfood', industry: 'restaurant' },
  { id: 'hotel-demo',   label: 'Motel One Bonn',        industry: 'hotel' },
  { id: 'praxis-demo',  label: 'Praxis Demo',           industry: 'medical' },
  { id: 'services-kmu', label: 'Beauty & Nails',        industry: 'services' },
];

function parseTenantYaml(content: string): { tenant_id?: string; industry?: string; practice?: { name?: string } } {
  // Minimal YAML field extraction (no yaml library dependency)
  const get = (key: string): string | undefined => {
    const match = content.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
    return match ? match[1].trim().replace(/^['"]|['"]$/g, '') : undefined;
  };
  const getPractice = (): string | undefined => {
    // Match "  name: Foo Bar" inside practice block
    const practiceMatch = content.match(/^practice:\s*\n((?:[ \t]+.+\n?)*)/m);
    if (!practiceMatch) return undefined;
    const nameMatch = practiceMatch[1].match(/\s+name:\s+(.+)/);
    return nameMatch ? nameMatch[1].trim().replace(/^['"]|['"]$/g, '') : undefined;
  };

  return {
    tenant_id: get('tenant_id'),
    industry: get('industry'),
    practice: { name: getPractice() },
  };
}

export async function GET() {
  try {
    // Try to read tenant configs from the voice agent directory
    const configDir = path.join(
      process.cwd(),
      '..', '..', '..', 'sailly-google-fork', 'configs', 'tenants'
    );

    if (!fs.existsSync(configDir)) {
      return NextResponse.json({ tenants: FALLBACK_TENANTS });
    }

    const files = fs.readdirSync(configDir).filter(f => f.endsWith('.yaml'));
    const tenants = [];

    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(configDir, file), 'utf-8');
        const parsed = parseTenantYaml(content);
        const tid = parsed.tenant_id || file.replace('.yaml', '');
        const industry = parsed.industry || 'services';
        const name = parsed.practice?.name || tid;

        tenants.push({
          id: tid,
          label: name,
          industry,
          industryLabel: INDUSTRY_LABELS[industry] || industry,
          icon: INDUSTRY_ICONS[industry] || '🏢',
        });
      } catch {
        // Skip malformed YAML files
      }
    }

    if (tenants.length === 0) {
      return NextResponse.json({ tenants: FALLBACK_TENANTS });
    }

    // Sort: put doboo first, then alphabetical
    tenants.sort((a, b) => {
      if (a.id === 'doboo') return -1;
      if (b.id === 'doboo') return 1;
      return a.label.localeCompare(b.label);
    });

    return NextResponse.json({ tenants });
  } catch {
    return NextResponse.json({ tenants: FALLBACK_TENANTS });
  }
}
