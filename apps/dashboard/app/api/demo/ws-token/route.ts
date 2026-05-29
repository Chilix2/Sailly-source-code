import { NextRequest, NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

const VOICE_AGENT_URL = process.env.VOICE_AGENT_URL || 'http://localhost:3003';
const JWT_SECRET = new TextEncoder().encode(
  process.env.DASHBOARD_JWT_SECRET || 'change-me-in-production'
);

export async function POST(req: NextRequest) {
  const token = req.cookies.get('access_token')?.value;
  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    await jwtVerify(token, JWT_SECRET);
  } catch {
    return NextResponse.json({ error: 'Invalid session' }, { status: 401 });
  }

  // Forward the access_token to the voice agent backend to get a one-time WS token
  const backendRes = await fetch(`${VOICE_AGENT_URL}/api/demo/ws-token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  if (!backendRes.ok) {
    return NextResponse.json({ error: 'Token service unavailable' }, { status: 503 });
  }

  const data = await backendRes.json();
  return NextResponse.json(data);
}
