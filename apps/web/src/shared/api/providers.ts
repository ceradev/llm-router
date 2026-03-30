const API_BASE = import.meta.env.PUBLIC_API_BASE_URL as string;

export type ProviderOption = {
  id: number;
  slug: string;
  display_name: string;
  is_active: boolean;
};

export async function fetchProviders(signal?: AbortSignal): Promise<ProviderOption[]> {
  const res = await fetch(`${API_BASE}/v1/providers`, { signal });
  if (!res.ok) throw new Error(`Providers ${res.status}`);
  const rows = (await res.json()) as ProviderOption[];
  return rows.filter((row) => row.is_active);
}
