#!/bin/bash
# Build script that handles CSS hash mapping for deployed standalone builds

set -e

echo "Building dashboard..."
npm run build

echo "Preparing standalone deployment..."
rm -rf .next/standalone/.next/static/
cp -r .next/static/. .next/standalone/.next/static/

echo "Mapping CSS hashes for RSC compatibility..."
# The Next.js RSC payload sometimes references different CSS hashes than what gets generated
# Copy the main CSS file to both known hashes to ensure compatibility
MAIN_CSS=$(ls .next/standalone/.next/static/css/ | grep -E '^[a-z0-9]{16}\.css$' | head -1)
if [ -n "$MAIN_CSS" ]; then
  echo "Main CSS: $MAIN_CSS"
  # This is a workaround for an issue where Next.js RSC generates different hashes
  # We're ensuring multiple hash versions of the CSS are available
  cp ".next/standalone/.next/static/css/$MAIN_CSS" ".next/standalone/.next/static/css/e999f596abe01186.css" 2>/dev/null || true
  cp ".next/standalone/.next/static/css/$MAIN_CSS" ".next/standalone/.next/static/css/b38ce4a5d64a8bcc.css" 2>/dev/null || true
fi

echo "Build and deployment prep complete!"
