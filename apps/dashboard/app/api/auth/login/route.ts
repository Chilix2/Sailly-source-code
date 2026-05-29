import { NextRequest, NextResponse } from 'next/server';
import { SignJWT } from 'jose';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:3002';
const JWT_SECRET = new TextEncoder().encode(
  process.env.DASHBOARD_JWT_SECRET || 'change-me-in-production'
);
const REFRESH_SECRET = new TextEncoder().encode(
  process.env.DASHBOARD_REFRESH_SECRET || 'change-me-in-production'
);

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { username, password, rememberMe } = body;

    if (!username || !password) {
      return NextResponse.json({ success: false, message: 'Username and password required' }, { status: 400 });
    }

    // Call backend to verify credentials
    const backendRes = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    const data = await backendRes.json();

    if (!backendRes.ok || !data.success) {
      return NextResponse.json(data, { status: backendRes.status });
    }

    const user = data.user;

    // Admin users get an effectively unlimited session (400 days = browser cookie max).
    // The middleware refreshes tokens on every authenticated request, so as long as the
    // admin is active the session never expires.
    const isAdmin = user.role === 'admin';
    const ADMIN_TTL_SECONDS = 400 * 24 * 60 * 60; // 400 days

    // Session duration: 1h default, 24h if "Stay logged in" checked. Admin overrides both.
    const accessTTL  = isAdmin ? `${ADMIN_TTL_SECONDS}s` : (rememberMe ? '4h'  : '1h');
    const refreshTTL = isAdmin ? `${ADMIN_TTL_SECONDS}s` : (rememberMe ? '24h' : '1h');
    const accessMaxAge  = isAdmin ? ADMIN_TTL_SECONDS : (rememberMe ? 4  * 60 * 60 : 60 * 60);
    const refreshMaxAge = isAdmin ? ADMIN_TTL_SECONDS : (rememberMe ? 24 * 60 * 60 : 60 * 60);

    const accessToken = await new SignJWT({ userId: user.id, username: user.username, role: user.role })
      .setProtectedHeader({ alg: 'HS256' })
      .setIssuedAt()
      .setExpirationTime(accessTTL)
      .sign(JWT_SECRET);

    const refreshToken = await new SignJWT({ userId: user.id, username: user.username, role: user.role })
      .setProtectedHeader({ alg: 'HS256' })
      .setIssuedAt()
      .setExpirationTime(refreshTTL)
      .sign(REFRESH_SECRET);

    const isProduction = process.env.NODE_ENV === 'production';

    const res = NextResponse.json({ success: true, user, sessionTTL: refreshMaxAge }, { status: 200 });

    res.cookies.set('access_token', accessToken, {
      httpOnly: true,
      secure: isProduction,
      sameSite: 'lax',
      path: '/',
      maxAge: accessMaxAge,
    });

    res.cookies.set('refresh_token', refreshToken, {
      httpOnly: true,
      secure: isProduction,
      sameSite: 'lax',
      path: '/',
      maxAge: refreshMaxAge,
    });

    return res;
  } catch (err) {
    console.error('[auth/login] error:', err);
    return NextResponse.json({ success: false, message: 'Auth service unavailable' }, { status: 503 });
  }
}
