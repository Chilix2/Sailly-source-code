const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3002';

export async function fetchAPI<T = any>(path: string, options?: RequestInit): Promise<{ success: boolean; data?: T; error?: string }> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      ...options,
    });
    const json = await res.json();
    if (!res.ok) {
      return { success: false, error: json.error || `HTTP ${res.status}` };
    }
    return json;
  } catch (err: any) {
    return { success: false, error: err.message || 'Network error' };
  }
}
