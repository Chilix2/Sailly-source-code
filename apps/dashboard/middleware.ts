import { NextRequest, NextResponse } from 'next/server';
import * as jose from 'jose';

const PUBLIC_PATHS = [
  '/login',
  '/demo-call',
  '/crucial-fix',
  '/api/auth',
  '/api/health',
  '/_next',
  '/favicon.ico',
  '/icon.svg',
  '/.well-known',
];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/') || pathname.startsWith(p));
}

const JWT_SECRET = new TextEncoder().encode(
  process.env.DASHBOARD_JWT_SECRET || 'change-me-in-production'
);

const REFRESH_SECRET = new TextEncoder().encode(
  process.env.DASHBOARD_REFRESH_SECRET || 'change-me-in-production'
);

async function verifyToken(token: string, secret: Uint8Array) {
  try {
    const { payload } = await jose.jwtVerify(token, secret);
    return payload as { userId: number; username: string; role: string };
  } catch {
    return null;
  }
}

async function createToken(
  payload: { userId: number; username: string; role: string },
  secret: Uint8Array,
  expiresInSeconds: number
): Promise<string> {
  return new jose.SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime(`${expiresInSeconds}s`)
    .sign(secret);
}

function addSecurityHeaders(response: NextResponse) {
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Permissions-Policy', 'camera=(), geolocation=()');
  response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  return response;
}

const COOKIE_OPTS = {
  httpOnly: true,
  secure: true,
  sameSite: 'lax' as const,
  path: '/',
};

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return addSecurityHeaders(NextResponse.next());
  }

  const accessToken = request.cookies.get('access_token')?.value;
  const refreshToken = request.cookies.get('refresh_token')?.value;

  if (!accessToken && !refreshToken) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  if (accessToken) {
    const payload = await verifyToken(accessToken, JWT_SECRET);
    if (payload) {
      const response = addSecurityHeaders(NextResponse.next());
      // Set a non-httpOnly cookie with the token expiry so the frontend can show a warning
      if (payload.exp) {
        response.cookies.set('session_expires', String(payload.exp), {
          httpOnly: false, secure: true, sameSite: 'lax', path: '/',
        });
      }
      return response;
    }
  }

  if (refreshToken) {
    const refreshPayload = await verifyToken(refreshToken, REFRESH_SECRET);
    if (!refreshPayload) {
      const res = NextResponse.redirect(new URL('/login', request.url));
      res.cookies.delete('access_token');
      res.cookies.delete('refresh_token');
      res.cookies.delete('session_expires');
      return res;
    }

    // Admin users get an effectively unlimited session (400 days = browser cookie max),
    // refreshed on every request so the session never expires while they are active.
    const isAdmin = refreshPayload.role === 'admin';
    const ADMIN_TTL_SECONDS = 400 * 24 * 60 * 60; // 400 days

    // Determine session type from refresh token TTL remaining
    const ttlRemaining = (refreshPayload.exp as number) - Math.floor(Date.now() / 1000);
    const isLongSession = ttlRemaining > 3600;
    const accessTTL  = isAdmin ? ADMIN_TTL_SECONDS : (isLongSession ? 4  * 3600 : 3600);
    const refreshTTL = isAdmin ? ADMIN_TTL_SECONDS : (isLongSession ? 24 * 3600 : 3600);

    const tokenData = { userId: refreshPayload.userId, username: refreshPayload.username, role: refreshPayload.role };
    const newAccess = await createToken(tokenData, JWT_SECRET, accessTTL);
    const newRefresh = await createToken(tokenData, REFRESH_SECRET, refreshTTL);

    const response = addSecurityHeaders(NextResponse.next());
    response.cookies.set('access_token', newAccess, { ...COOKIE_OPTS, maxAge: accessTTL });
    response.cookies.set('refresh_token', newRefresh, { ...COOKIE_OPTS, maxAge: refreshTTL });
    const newExp = Math.floor(Date.now() / 1000) + accessTTL;
    response.cookies.set('session_expires', String(newExp), {
      httpOnly: false, secure: true, sameSite: 'lax', path: '/',
    });
    return response;
  }

  return NextResponse.redirect(new URL('/login', request.url));
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icon.svg).*)'],
};
