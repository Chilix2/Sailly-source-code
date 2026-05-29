const config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                // Sailly custom colors (preserved for existing components)
                background: "#0b1628",
                surface: "#0e1e35",
                surface2: "#132540",
                border: "#1a3050",
                "border-glow": "#2a5080",
                accent: "hsl(180 100% 50%)",
                "accent-2": "hsl(270 85% 50%)",
                "accent-3": "hsl(160 85% 45%)",
                "accent-warn": "hsl(38 90% 55%)",
                "accent-danger": "hsl(0 90% 55%)",
                text: "hsl(210 17% 88%)",
                "text-muted": "hsl(210 11% 45%)",
                "text-dim": "hsl(210 8% 58%)",
                // shadcn/ui colors (from CSS variables)
                "background-shade": "hsl(var(--background-shade) / <alpha-value>)",
                "foreground-shade": "hsl(var(--foreground-shade) / <alpha-value>)",
                "card-shade": "hsl(var(--card-shade) / <alpha-value>)",
                "card-foreground-shade": "hsl(var(--card-foreground-shade) / <alpha-value>)",
                "popover-shade": "hsl(var(--popover-shade) / <alpha-value>)",
                "muted-shade": "hsl(var(--muted-shade) / <alpha-value>)",
                "muted-foreground-shade": "hsl(var(--muted-foreground-shade) / <alpha-value>)",
                "accent-shade": "hsl(var(--accent-shade) / <alpha-value>)",
                "destructive-shade": "hsl(var(--destructive-shade) / <alpha-value>)",
                "border-shade": "hsl(var(--border-shade) / <alpha-value>)",
                "input-shade": "hsl(var(--input-shade) / <alpha-value>)",
                "ring-shade": "hsl(var(--ring-shade) / <alpha-value>)",
            },
            fontFamily: {
                sans: ['"Geist"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
                mono: ['"JetBrains Mono"', 'monospace'],
            },
            backgroundImage: {
                glow: "radial-gradient(circle, rgba(0,212,255,0.08) 0%, transparent 70%)",
                "glow-purple": "radial-gradient(circle, rgba(124,58,237,0.08) 0%, transparent 70%)",
            },
            backdropBlur: {
                glass: "12px",
            },
            animation: {
                "pulse-gentle": "pulse-gentle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                "fade-up": "fade-up 0.6s ease forwards",
            },
            keyframes: {
                "pulse-gentle": {
                    "0%, 100%": { opacity: "1" },
                    "50%": { opacity: "0.7" },
                },
                "fade-up": {
                    from: { opacity: "0", transform: "translateY(12px)" },
                    to: { opacity: "1", transform: "translateY(0)" },
                },
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
        },
    },
    plugins: [],
};
export default config;
