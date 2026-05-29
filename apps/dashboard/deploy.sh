#!/bin/bash
set -e
cd /home/charles2/sailly/apps/dashboard

export PATH=/home/charles2/.nvm/versions/node/v20.20.1/bin:$PATH

echo "Building..."
npm run build

echo "Copying static files to standalone..."
rm -rf .next/standalone/.next/static
cp -r .next/static .next/standalone/.next/static

if [ -d "public" ]; then
  cp -r public .next/standalone/public 2>/dev/null || true
fi

echo "Restarting dashboard..."
sudo systemctl restart sailly-dashboard

echo "Done. Verifying..."
sleep 4
BUILD=$(cat .next/standalone/.next/BUILD_ID)
echo "  Build ID: $BUILD"
curl -s -o /dev/null -w "  /demo-call: HTTP %{http_code}\n" https://sailly.tech/demo-call
