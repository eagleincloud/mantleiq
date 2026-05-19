import React from 'react'
import { formatScore, formatPercent, formatRank } from '../utils/formatters'

export default function RankingList({ zones, selectedZone, onSelect, loading }) {
  const getScoreColor = (score) => {
    if (score >= 80) return 'text-red-600 bg-red-50'
    if (score >= 65) return 'text-orange-600 bg-orange-50'
    if (score >= 50) return 'text-teal-600 bg-teal-50'
    return 'text-gray-600 bg-gray-50'
  }

  const sortedZones = [...zones].sort((a, b) => {
    const scoreA = (a.properties?.prospectivity_score || 0)
    const scoreB = (b.properties?.prospectivity_score || 0)
    return scoreB - scoreA
  })

  if (loading) {
    return <div className="text-center text-gray-500 py-4">Loading zones...</div>
  }

  if (zones.length === 0) {
    return <div className="text-center text-gray-500 text-sm py-4">No zones found</div>
  }

  return (
    <div className="space-y-2">
      {sortedZones.slice(0, 20).map((feature, idx) => {
        const props = feature.properties || {}
        const score = props.prospectivity_score !== null ? props.prospectivity_score * 100 : null
        const confidence = props.confidence !== null ? props.confidence * 100 : null
        const isSelected = selectedZone?.properties?.id === props.id
        const displayScore = score !== null ? score.toFixed(0) : '--'

        return (
          <button
            key={props.id || `cell-${props.grid_x}-${props.grid_y}-${idx}`}
            onClick={() => onSelect(feature)}
            className={`w-full text-left p-3 rounded-lg border transition-colors ${
              isSelected
                ? 'border-teal-500 bg-teal-50'
                : 'border-gray-200 bg-white hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="font-medium text-gray-900">
                  Cell {props.grid_x !== null ? props.grid_x : '--'},{props.grid_y !== null ? props.grid_y : '--'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Rank: {formatRank(props.rank, idx)}
                </p>
              </div>
              <div className={`font-bold text-lg px-3 py-1 rounded ${getScoreColor(score || 0)}`}>
                {displayScore}
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-600">
              Confidence: {confidence !== null ? confidence.toFixed(0) : '--'}%
            </div>
          </button>
        )
      })}
    </div>
  )
}
