import { safeFetch } from './safeFetch';

const BASE = import.meta.env.VITE_OPTIMIZATION_API ?? 'http://localhost:8003';

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DimRange { min: number; max: number }
export interface ContainerDims {
  length: DimRange;
  height: DimRange;
  width: DimRange;
}
export interface InnerMargin { length: number; height: number; width: number }

export interface RuleConstraint {
  orientation_locked: boolean;
  locked_axis: string | null;
  max_stack_layers: number | null;
}

export interface Container {
  id: string;
  name: string;
  description?: string;
  dims_cm: ContainerDims;
  wall_thickness_mm: number;
  inner_margin_cm: InnerMargin;
  max_weight_kg: number;
  max_air_pct: number;
  priority: number;
  active: boolean;
  local_rules: unknown[];
}

export interface ContainerCreate {
  name: string;
  description?: string;
  dims_cm: ContainerDims;
  wall_thickness_mm?: number;
  inner_margin_cm?: InnerMargin;
  max_weight_kg: number;
  max_air_pct?: number;
  priority?: number;
  active?: boolean;
}

export interface Rule {
  id: string;
  name: string;
  description?: string;
  constraint: RuleConstraint;
  active: boolean;
}

export interface RuleCreate {
  name: string;
  description?: string;
  constraint: RuleConstraint;
  active?: boolean;
}

export interface AssignmentFilter {
  family_id: string;
  subfamily_ids: string[];
}

export interface RuleAssignment {
  id: string;
  rule_id: string;
  filter: AssignmentFilter;
  active: boolean;
}

export interface RuleAssignmentCreate {
  rule_id: string;
  filter?: AssignmentFilter;
  active?: boolean;
}

// ── Renders ───────────────────────────────────────────────────────────────────

export async function fetchContainerRenderHtml(token: string, id: string): Promise<string> {
  const res = await safeFetch(`${BASE}/renders/container/${id}`, { headers: authHeader(token) });
  if (!res.ok) throw new Error('render failed');
  return res.text();
}

export async function fetchRuleRenderHtml(token: string, ruleId: string): Promise<string> {
  const res = await safeFetch(`${BASE}/renders/rule/${ruleId}`, { headers: authHeader(token) });
  if (!res.ok) throw new Error('rule render failed');
  return res.text();
}

export async function fetchPreviewRenderHtml(
  token: string,
  dims: { length_min: number; length_max: number; height_min: number; height_max: number; width_min: number; width_max: number },
): Promise<string> {
  const res = await safeFetch(`${BASE}/renders/preview`, {
    method: 'POST',
    headers: { ...authHeader(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(dims),
  });
  if (!res.ok) throw new Error('preview render failed');
  return res.text();
}

// ── Containers ────────────────────────────────────────────────────────────────

export async function listContainers(token: string): Promise<Container[]> {
  const res = await safeFetch(`${BASE}/containers/all`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching containers');
  return res.json();
}

export async function deleteContainer(token: string, id: string): Promise<void> {
  const res = await safeFetch(`${BASE}/containers/${id}`, {
    method: 'DELETE',
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error deleting container');
}

export async function createContainer(token: string, data: ContainerCreate): Promise<Container> {
  const res = await safeFetch(`${BASE}/containers/`, {
    method: 'POST',
    headers: authHeader(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error creating container');
  return res.json();
}

export async function updateContainer(token: string, id: string, data: Partial<ContainerCreate & { active: boolean }>): Promise<Container> {
  const res = await safeFetch(`${BASE}/containers/${id}`, {
    method: 'PUT',
    headers: authHeader(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error updating container');
  return res.json();
}

// ── Rules ─────────────────────────────────────────────────────────────────────

export async function listRules(token: string): Promise<Rule[]> {
  const res = await safeFetch(`${BASE}/rules/all`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching rules');
  return res.json();
}

export async function createRule(token: string, data: RuleCreate): Promise<Rule> {
  const res = await safeFetch(`${BASE}/rules/`, {
    method: 'POST',
    headers: authHeader(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error creating rule');
  return res.json();
}

// ── Rule Assignments ───────────────────────────────────────────────────────────

export async function listRuleAssignments(token: string): Promise<RuleAssignment[]> {
  const res = await safeFetch(`${BASE}/rule-assignments/all`, { headers: authHeader(token) });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error fetching assignments');
  return res.json();
}

export async function createRuleAssignment(token: string, data: RuleAssignmentCreate): Promise<RuleAssignment> {
  const res = await safeFetch(`${BASE}/rule-assignments/`, {
    method: 'POST',
    headers: authHeader(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error creating assignment');
  return res.json();
}

export async function deleteRuleAssignment(token: string, id: string): Promise<void> {
  const res = await safeFetch(`${BASE}/rule-assignments/${id}`, {
    method: 'DELETE',
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Error deleting assignment');
}
