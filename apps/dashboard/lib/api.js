const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3002';
export async function fetchAPI(path, options) {
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
    }
    catch (err) {
        return { success: false, error: err.message || 'Network error' };
    }
}
