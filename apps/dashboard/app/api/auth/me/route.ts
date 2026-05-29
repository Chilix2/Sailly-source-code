import { NextRequest, NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

export async function GET(req: NextRequest) {
  const token = req.cookies.get('access_token')?.value;
  if (!token) return NextResponse.json({ success: false, message: 'Unauthorized' }, { status: 401 });

  try {
    const secret = new TextEncoder().encode(
      process.env.DASHBOARD_JWT_SECRET || 'change-me-in-production'
    );
    const { payload } = await jwtVerify(token, secret);
    return NextResponse.json({
      success: true,
      user: {
        username: payload['username'],
        role: payload['role'],
        userId: payload['userId'],
      },
    });
  } catch {
    return NextResponse.json({ success: false, message: 'Invalid token' }, { status: 401 });
  }
}
