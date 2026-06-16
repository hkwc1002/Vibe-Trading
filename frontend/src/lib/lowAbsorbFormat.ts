export function toFiniteNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatCnyYi(value: string | number | null | undefined, precision = 1): string {
  const parsed = toFiniteNumber(value);
  if (parsed === null) return "—";
  return `${(parsed / 100000000).toFixed(precision)} 亿`;
}

export function formatCnySmart(value: string | number | null | undefined): string {
  const parsed = toFiniteNumber(value);
  if (parsed === null) return "—";
  const abs = Math.abs(parsed);
  if (abs >= 100000000) return `${(parsed / 100000000).toFixed(1)} 亿`;
  if (abs >= 10000) return `${(parsed / 10000).toFixed(1)} 万`;
  return `${parsed.toFixed(2)} 元`;
}

export function formatPctDecimal(value: string | number | null | undefined, precision = 2): string {
  const parsed = toFiniteNumber(value);
  if (parsed === null) return "—";
  return `${(parsed * 100).toFixed(precision)}%`;
}

export function formatRatio(value: string | number | null | undefined, precision = 2): string {
  const parsed = toFiniteNumber(value);
  if (parsed === null) return "—";
  return parsed.toFixed(precision);
}
