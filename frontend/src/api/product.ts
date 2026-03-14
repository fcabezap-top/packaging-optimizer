import { safeFetch } from './safeFetch';

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

export interface ProductSize {
  id: string;
  name: string;
  order: number;
}

export interface ProductDetail {
  id: string;
  name: string;
  description: string;
  ean_code: string;
  manufacturer_id: string;
  family_id: string;
  subfamily_id: string;
  campaign_id: string;
  sizes: ProductSize[];
  family: Family;
  subfamily: Subfamily;
  campaign: { id: string; name: string };
}

export async function listFamilies(token: string): Promise<Family[]> {
  const res = await safeFetch(`${BASE}/families/`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching families');
  return res.json();
}

export async function listSubfamilies(token: string): Promise<Subfamily[]> {
  const res = await safeFetch(`${BASE}/subfamilies/`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching subfamilies');
  return res.json();
}

export async function fetchAllProducts(token: string): Promise<ProductDetail[]> {
  const res = await safeFetch(`${BASE}/products/`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching products');
  return res.json();
}

export async function fetchMyProducts(token: string): Promise<ProductDetail[]> {
  const res = await safeFetch(`${BASE}/products/mine`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching products');
  return res.json();
}

export async function fetchProduct(token: string, id: string): Promise<ProductDetail> {
  const res = await safeFetch(`${BASE}/products/${id}`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Product not found');
  return res.json();
}

