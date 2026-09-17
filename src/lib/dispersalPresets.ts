export interface DispersalPreset {
  id: string
  label: string
  distance: number | null
}

export const DISPERSAL_PRESETS: DispersalPreset[] = [
  { id: 'anfibios', label: 'Anfibios (~150 m)', distance: 150 },
  { id: 'micromamiferos', label: 'Micromamíferos (~300 m)', distance: 300 },
  { id: 'aves', label: 'Aves forestales (~800 m)', distance: 800 },
  { id: 'custom', label: 'Personalizado', distance: null },
]

export function presetForDistance(distance: number): DispersalPreset {
  return DISPERSAL_PRESETS.find((p) => p.distance === distance) ?? DISPERSAL_PRESETS[DISPERSAL_PRESETS.length - 1]
}
