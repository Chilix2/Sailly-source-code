import os
import re
import glob

replacements_general = {
    r'bg-zinc-800/20': 'bg-[#fcfaf9]',
    r'bg-zinc-800/30': 'bg-brand-cream',
    r'bg-zinc-800/40': 'bg-[#ecd8d3]',
    r'bg-zinc-900': 'bg-[#fcfaf9]',
    r'bg-zinc-600': 'bg-[#dfcdc7]',
    r'text-zinc-600': 'text-brand-muted',
    r'text-zinc-500': 'text-brand-muted',
    r'text-zinc-400': 'text-brand-slate',
    r'bg-red-950/30': 'bg-[#fff0ee]',
    r'bg-red-950/50': 'bg-[#fff0ee]',
    r'text-red-300': 'text-brand-salmon',
    r'border-red-900/50': 'border-[#ffd8d0]',
    r'bg-yellow-950/30': 'bg-[#fff8ea]',
    r'bg-yellow-950/50': 'bg-[#fff8ea]',
    r'text-yellow-300': 'text-brand-peach',
    r'border-yellow-900/50': 'border-[#ffe4cc]',
    r'bg-blue-950/30': 'bg-[#f4f7fb]',
    r'text-blue-300': 'text-brand-slate',
    r'border-blue-900/50': 'border-[#dce5f0]',
    r'bg-green-950/50': 'bg-[#f0fdf4]',
    r'text-green-300': 'text-[#16a34a]',
    r'text-green-400': 'text-[#16a34a]',
    r'text-green-500': 'text-[#16a34a]',
    r'text-red-400': 'text-brand-salmon',
    r'text-red-500': 'text-brand-salmon'
}

files = glob.glob('/home/charles2/sailly/apps/dashboard/app/**/*.tsx', recursive=True) + \
        glob.glob('/home/charles2/sailly/apps/dashboard/components/**/*.tsx', recursive=True)

# sort by length so longer patterns get replaced first
sorted_reps_general = sorted(replacements_general.items(), key=lambda x: len(x[0]), reverse=True)

exclude_white = [
    '/home/charles2/sailly/apps/dashboard/app/demo-call/page.tsx',
    '/home/charles2/sailly/apps/dashboard/app/login/page.tsx',
    '/home/charles2/sailly/apps/dashboard/components/Sidebar.tsx'
]

for fpath in files:
    with open(fpath, 'r') as f:
        content = f.read()
    
    original = content
    
    for pattern, rep in sorted_reps_general:
        content = re.sub(r'(?<=[\s"\'`])' + re.escape(pattern) + r'(?=[\s"\'`])', rep, content)
        
    if fpath not in exclude_white:
        # replace text-white with text-brand-navy
        content = re.sub(r'(?<=[\s"\'`])text-white(?=[\s"\'`])', 'text-brand-navy', content)
        
    if original != content:
        with open(fpath, 'w') as f:
            f.write(content)
        print(f"Updated {fpath}")
