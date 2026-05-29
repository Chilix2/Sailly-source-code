import { NextResponse } from 'next/server';
import * as jose from 'jose';
const PUBLIC_PATHS = [
    '/login',
    '/demo-call',
    '/api/auth',
    '/api/health',
    '/_next',
    '/favicon.ico',
    '/.well-known',
];
function isPublicPath(pathname) {
    return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/') || pathname.startsWith(p));
}
const JWT_SECRET = new TextEncoder().encode(process.env.DASHBOARD_JWT_SECRET || 'change-me-in-production');
const REFRESH_SECRET = new TextEncoder().encode(process.env.DASHBOARD_REFRESH_SECRET || 'change-me-in-production');
async function verifyToken(token, secret) {
    try {
        const { payload } = await jose.jwtVerify(token, secret);
        return payload;
    }
    catch {
        return null;
    }
}
async function createToken(payload, secret, expiresInSeconds) {
    return new jose.SignJWT(payload)
        .setProtectedHeader({ alg: 'HS256' })
        .setExpirationTime(`${expiresInSeconds}s`)
        .sign(secret);
}
function addSecurityHeaders(response) {
    response.headers.set('X-Frame-Options', 'DENY');
    response.headers.set('X-Content-Type-Options', 'nosniff');
    response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
    response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
    return response;
}
const COOKIE_OPTS = {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
};
export async function middleware(request) {
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
            return addSecurityHeaders(NextResponse.next());
        }
    }
    if (refreshToken) {
        const refreshPayload = await verifyToken(refreshToken, REFRESH_SECRET);
        if (!refreshPayload) {
            const res = NextResponse.redirect(new URL('/login', request.url));
            res.cookies.delete('access_token');
            res.cookies.delete('refresh_token');
            return res;
        }
        const tokenData = { userId: refreshPayload.userId, username: refreshPayload.username, role: refreshPayload.role };
        const newAccess = await createToken(tokenData, JWT_SECRET, 15 * 60);
        const newRefresh = await createToken(tokenData, REFRESH_SECRET, 7 * 24 * 60 * 60);
        const response = addSecurityHeaders(NextResponse.next());
        response.cookies.set('access_token', newAccess, { ...COOKIE_OPTS, maxAge: 15 * 60 });
        response.cookies.set('refresh_token', newRefresh, { ...COOKIE_OPTS, maxAge: 7 * 24 * 60 * 60 });
        return response;
    }
    return NextResponse.redirect(new URL('/login', request.url));
}
export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
