import { NextResponse } from 'next/server';
export async function POST() {
    const res = NextResponse.json({ success: true, message: 'Logged out' });
    res.cookies.set('access_token', '', { maxAge: 0, path: '/', httpOnly: true });
    res.cookies.set('refresh_token', '', { maxAge: 0, path: '/', httpOnly: true });
    return res;
}
