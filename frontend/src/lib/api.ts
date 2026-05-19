export type TrustCheck = {
  key: string;
  name: string;
  status: "pass" | "weak" | "missing";
  note: string;
  evidence: string;
};

export type ConflictSide = {
  page_url: string;
  page_intent: string;
  value: string;
  snippet: string;
};

export type Conflict = {
  topic: string;
  description: string;
  sides: ConflictSide[];
};

export type FormField = {
  name: string;
  label: string;
  type: string;
  required: boolean;
  is_essential: boolean;
  reason: string;
};

export type FormFinding = {
  page_url: string;
  page_intent: string;
  total_fields: number;
  required_fields: number;
  essential_required: number;
  extra_required: number;
  fields: FormField[];
};

export type FormAudit = {
  forms: FormFinding[];
  monthly_visitors: number;
  form_reach_rate: number;
  avg_order_value: number;
  per_field_drop: number;
  extra_required_total: number;
  estimated_monthly_loss_usd: number;
  notes: string[];
};

export type AnalyzeResponse = {
  ok: boolean;
  url: string;
  base_url: string;
  fetched_pages: { fetched: number; failed: number; urls: string[] };
  teaser_score: number;
  teaser_loss_usd: number;
  teaser_locked: boolean;
  score: number | null;
  score_breakdown: { trust: number; consistency: number; form: number } | null;
  trust: TrustCheck[];
  conflicts_count: number;
  conflicts: Conflict[] | null;
  forms_summary: {
    forms_found: number;
    extra_required_total: number;
    estimated_monthly_loss_usd: number;
    report_id?: string;
    real_score_locked?: boolean;
  };
  forms: FormAudit | null;
  actions: { title: string; when: string; detail: string }[];
  error: string;
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchConfig() {
  const r = await fetch(`${API}/config`);
  return r.json() as Promise<{
    stripe_enabled: boolean;
    unlock_price_cents: number;
    unlock_price_display: string;
  }>;
}

export async function analyze(opts: {
  url: string;
  monthly_visitors?: number;
  avg_order_value?: number;
  unlock?: string;
}): Promise<AnalyzeResponse> {
  const qs = opts.unlock ? `?unlock=${encodeURIComponent(opts.unlock)}` : "";
  const r = await fetch(`${API}/analyze${qs}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      url: opts.url,
      monthly_visitors: opts.monthly_visitors ?? 5000,
      avg_order_value: opts.avg_order_value ?? 200,
    }),
  });
  if (!r.ok) {
    let detail = "";
    try {
      detail = (await r.json()).detail || "";
    } catch {}
    throw new Error(detail || `HTTP ${r.status}`);
  }
  return r.json();
}

export async function checkout(report_id: string, url: string) {
  const r = await fetch(`${API}/checkout`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ report_id, url }),
  });
  return r.json() as Promise<{
    ok: boolean;
    enabled: boolean;
    url: string;
    error: string;
  }>;
}

export const apiBase = API;
