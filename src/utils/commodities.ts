export const COMMODITY_LABELS: Record<string, string> = {
  ganado: 'Ganado',
  cacao: 'Cacao',
  cafe: 'Café',
  aceite_palma: 'Aceite de palma',
  soja: 'Soja',
  caucho: 'Caucho',
  madera: 'Madera',
}

export function commodityLabel(commodity: string | null): string | null {
  if (!commodity) return null
  return COMMODITY_LABELS[commodity] ?? commodity
}
