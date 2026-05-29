import { NextResponse } from 'next/server';
import { SignJWT } from 'jose';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:3002';
const JWT_SECRET = new TextEncoder().encode(process.env.DASHBOARD_JWT_SECRET || 'change-me-in-production');
const REFRESH_SECRET = new TextEncoder().encode(process.env.DASHBOARD_REFRESH_SECRET || 'change-me-in-production');
export async function POST(req) {
    try {
        const body = await req.json();
        const { username, password } = body;
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
        // Generate JWT tokens here (on the dashboard domain) so cookies are set correctly
        const now = Math.floor(Date.now() / 1000);
        const accessToken = await new SignJWT({ userId: user.id, username: user.username, role: user.role })
            .setProtectedHeader({ alg: 'HS256' })
            .setIssuedAt()
            .setExpirationTime('15m')
            .sign(JWT_SECRET);
        const refreshToken = await new SignJWT({ userId: user.id, username: user.username, role: user.role })
            .setProtectedHeader({ alg: 'HS256' })
            .setIssuedAt()
            .setExpirationTime('7d')
            .sign(REFRESH_SECRET);
        const isProduction = process.env.NODE_ENV === 'production';
        const res = NextResponse.json({ success: true, user }, { status: 200 });
        res.cookies.set('access_token', accessToken, {
            httpOnly: true,
            secure: isProduction,
            sameSite: 'lax',
            path: '/',
            maxAge: 15 * 60, // 15 minutes
        });
        res.cookies.set('refresh_token', refreshToken, {
            httpOnly: true,
            secure: isProduction,
            sameSite: 'lax',
            path: '/',
            maxAge: 7 * 24 * 60 * 60, // 7 days
        });
        return res;
    }
    catch (err) {
        console.error('[auth/login] error:', err);
        return NextResponse.json({ success: false, message: 'Auth service unavailable' }, { status: 503 });
    }
}
