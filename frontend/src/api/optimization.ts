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
  dims: { length_min: number; length_max: number; height_min: number; height_max: number; width_min: number; width_max: number; wall_thickness_mm?: number },
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

// ── Proposals ───────────────────────────────────────────────────────────────

export interface ProposalSummary {
  id: string;
  product_id: string;
  size_id: string;
  status: string;
  created_at: string;
}

export async function listProposals(token: string, productId?: string): Promise<ProposalSummary[]> {
  const params = productId ? `?product_id=${encodeURIComponent(productId)}` : '';
  const res = await safeFetch(`${BASE}/proposals/${params}`, { headers: authHeader(token) });
  if (!res.ok) throw new Error('Error fetching proposals');
  return res.json();
}

export interface ProposalCreateBody {
  product_id: string;
  size_id: string;
  article_dims: { length_cm: number; width_cm: number; height_cm: number; weight_kg: number };
  lot_size: number;
  inner_wall_thickness_mm: number;
}

export interface ProposalResult {
  id: string;
  product_id: string;
  size_id: string;
  article_dims: { length_cm: number; width_cm: number; height_cm: number; weight_kg: number } | null;
  lot_size: number;
  status: string;
  created_at: string;
  render_html: string | null;
  inner_box: {
    ext_max_cm: number; ext_med_cm: number; ext_min_cm: number;
    int_max_cm: number; int_med_cm: number; int_min_cm: number;
    total_weight_kg: number;
    wall_thickness_mm: number;
    grid: number[];
  } | null;
  selected_master: {
    container_id: string;
    container_name: string;
    container_priority: number | null;
    inners_used: number;
    fill_pct: number;
    air_pct: number;
    total_weight_kg: number;
    accepted: boolean;
    ext_dims: number[];
    util_dims: number[];
    grid: number[];
    inner_dims_rotated: number[];
  } | null;
  all_evaluated: Array<{
    container_name: string;
    fill_pct: number;
    air_pct: number;
    inners_used: number;
    accepted: boolean;
  }> | null;
  pdf_b64: string | null;
}

export async function submitProposal(token: string, body: ProposalCreateBody): Promise<ProposalResult> {
  const res = await safeFetch(`${BASE}/proposals/optimize`, {
    method: 'POST',
    headers: authHeader(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().then((j: { detail?: string }) => j.detail).catch(() => null);
    throw new Error(detail ?? 'Error generating proposal');
  }
  return res.json();
}

export async function getProposalById(token: string, id: string): Promise<ProposalResult> {
  const res = await safeFetch(`${BASE}/proposals/${id}`, { headers: authHeader(token) });
  if (!res.ok) throw new Error('Error fetching proposal');
  return res.json();
}

export async function fetchProposalRenderHtml(token: string, id: string): Promise<string> {
  const res = await safeFetch(`${BASE}/renders/proposal/${id}`, { headers: authHeader(token) });
  if (!res.ok) throw new Error('proposal render failed');
  return res.text();
}

export async function recalculateProposal(token: string, id: string, body: ProposalCreateBody): Promise<ProposalResult> {
  const res = await safeFetch(`${BASE}/proposals/${id}/recalculate`, {
    method: 'PUT',
    headers: authHeader(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().then((j: { detail?: string }) => j.detail).catch(() => null);
    throw new Error(detail ?? 'Error recalculating proposal');
  }
  return res.json();
}

/** Fetch full proposals (including inner_box, selected_master, etc.) for a product. */
export async function fetchProductProposals(token: string, productId: string): Promise<ProposalResult[]> {
  const res = await safeFetch(`${BASE}/proposals/?product_id=${encodeURIComponent(productId)}`, {
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error('Error fetching proposals');
  return res.json();
}

/** Run the optimization pipeline without saving to the database. */
export async function calculateProposal(token: string, body: ProposalCreateBody): Promise<ProposalResult> {
  const res = await safeFetch(`${BASE}/proposals/calculate`, {
    method: 'POST',
    headers: authHeader(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().then((j: { detail?: string }) => j.detail).catch(() => null);
    throw new Error(detail ?? 'Error calculating proposal');
  }
  return res.json();
}

export async function updateProposalStatus(
  token: string,
  id: string,
  proposalStatus: 'accepted' | 'rejected' | 'pending',
  rejectionReason?: string,
): Promise<ProposalResult> {
  const res = await safeFetch(`${BASE}/proposals/${id}/status`, {
    method: 'PATCH',
    headers: authHeader(token),
    body: JSON.stringify({ status: proposalStatus, rejection_reason: rejectionReason ?? null }),
  });
  if (!res.ok) {
    const detail = await res.json().then((j: { detail?: string }) => j.detail).catch(() => null);
    throw new Error(detail ?? 'Error updating proposal status');
  }
  return res.json();
}
