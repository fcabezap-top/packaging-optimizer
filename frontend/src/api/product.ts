const BASE = import.meta.env.VITE_PRODUCT_API ?? 'http://localhost:8002';

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

export interface Family {
  id: string;
  name: string;
  family_code: number;
}

export interface Subfamily {
  id: string;
  name: string;
  subfamily_code: number;
  family_id: string;
}

export async function listFamilies(token: string): Promise<Family[]> {
  const res = await fetch(`${BASE}/families/`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching families');
  return res.json();
}

export async function listSubfamilies(token: string): Promise<Subfamily[]> {
  const res = await fetch(`${BASE}/subfamilies/`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching subfamilies');
  return res.json();
}
