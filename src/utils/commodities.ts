export const COMMODITY_LABELS: Record<string, string> = {
  cafe: 'Café',
  cacao: 'Cacao',
  soja: 'Soja',
  madera: 'Madera',
}

export function commodityLabel(commodity: string | null): string | null {
  if (!commodity) return null
  return COMMODITY_LABELS[commodity] ?? commodity
}
