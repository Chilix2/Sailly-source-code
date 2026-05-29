import re

files_to_update = [
    '/home/charles2/sailly/apps/dashboard/components/Sidebar.tsx',
    '/home/charles2/sailly/apps/dashboard/app/overview/page.tsx',
    '/home/charles2/sailly/apps/dashboard/app/demo-call/page.tsx'
]

for fpath in files_to_update:
    with open(fpath, 'r') as f:
        content = f.read()

    # Find <Icon size={...} /> or <SpecificIcon size={...} /> and inject fill="currentColor"
    # We will use regex to find `<[A-Z][a-zA-Z0-9]*\s+size={[^}]+}(?:\s+className="[^"]+")?\s*/>`
    # and add `fill="currentColor"`
    # But some icons might already have fill, or it's simpler:
    content = re.sub(
        r'(<[A-Z][a-zA-Z0-9]*\s+size={[0-9]+}(?:\s+className="[^"]*")?)\s*/>',
        r'\1 fill="currentColor" />',
        content
    )
    
    with open(fpath, 'w') as f:
        f.write(content)

print("Icons updated.")
