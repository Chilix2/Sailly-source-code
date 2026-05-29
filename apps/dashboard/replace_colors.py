import os
import re
import glob

replacements = {
    r'bg-zinc-950': 'bg-[#fcfaf9]',
    r'bg-zinc-900/50': 'bg-white/50 shadow-sm',
    r'bg-zinc-900/80': 'bg-white/80 shadow-sm',
    r'bg-zinc-900': 'bg-white shadow-sm',
    r'bg-zinc-800/50': 'bg-brand-cream',
    r'bg-zinc-800/70': 'bg-[#ecd8d3]',
    r'bg-zinc-800/80': 'bg-[#ecd8d3]',
    r'bg-zinc-800': 'bg-brand-cream',
    r'bg-zinc-700/30': 'bg-[#ecd8d3]/30',
    r'bg-zinc-700': 'bg-[#e8d8d2]',
    
    r'hover:bg-zinc-900/30': 'hover:bg-brand-cream/50',
    r'hover:bg-zinc-900/50': 'hover:bg-brand-cream',
    r'hover:bg-zinc-900/80': 'hover:bg-white',
    r'hover:bg-zinc-800/50': 'hover:bg-[#ecd8d3]',
    r'hover:bg-zinc-800': 'hover:bg-[#e8d8d2]',
    r'hover:bg-zinc-700': 'hover:bg-[#dfcdc7]',
    
    r'border-zinc-800/50': 'border-brand-cream',
    r'border-zinc-800': 'border-brand-cream',
    r'border-zinc-700': 'border-[#e8d8d2]',
    r'hover:border-zinc-700': 'hover:border-[#dfcdc7]',
    r'hover:border-zinc-300': 'hover:border-brand-slate',
    
    r'text-zinc-950': 'text-white',
    r'text-zinc-600': 'text-brand-muted',
    r'text-zinc-500': 'text-brand-muted',
    r'text-zinc-400': 'text-brand-slate',
    r'text-zinc-300': 'text-brand-navy',
    r'text-zinc-200': 'text-brand-navy',
    
    r'hover:text-zinc-200': 'hover:text-brand-pink',
    r'text-accent': 'text-brand-pink',
    r'bg-accent': 'bg-brand-pink',
    r'border-accent/40': 'border-brand-pink/40',
    r'border-accent/20': 'border-brand-pink/20',
    r'bg-accent/5': 'bg-brand-pink/5',
    r'bg-background': 'bg-transparent',
    
    r'border-red-500/30': 'border-brand-salmon/30',
    r'border-yellow-500/30': 'border-brand-peach/30',
    r'border-blue-500/20': 'border-blue-500/10',

    r'bg-zinc-700/30 text-zinc-400': 'bg-brand-cream text-brand-slate'
}

# sort by length so longer patterns get replaced first
sorted_reps = sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True)

files = glob.glob('/home/charles2/sailly/apps/dashboard/app/**/*.tsx', recursive=True) + \
        glob.glob('/home/charles2/sailly/apps/dashboard/components/**/*.tsx', recursive=True)

for fpath in files:
    with open(fpath, 'r') as f:
        content = f.read()
    
    original = content
    for pattern, rep in sorted_reps:
        # Use word boundaries for safe replacement, avoiding replacing partial matches
        # Need to handle tailwind classes which have slashes and colons
        # So boundary is space or quote
        content = re.sub(r'(?<=[\s"\'`])' + re.escape(pattern) + r'(?=[\s"\'`])', rep, content)
        
    if original != content:
        with open(fpath, 'w') as f:
            f.write(content)
        print(f"Updated {fpath}")
