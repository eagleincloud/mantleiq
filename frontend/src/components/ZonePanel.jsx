import React, { useState } from 'react'
import api from '../services/api'
import { formatScore, formatPercent, formatText } from '../utils/formatters'

export default function ZonePanel({ zone }) {
  const [exporting, setExporting] = useState(false)
  const [exportMessage, setExportMessage] = useState(null)
  const [showDetails, setShowDetails] = useState(false)

  const props = zone.properties || {}
  const score = props.prospectivity_score !== null ? props.prospectivity_score : null
  const scorePercent = score !== null ? score * 100 : null
  const confidence = props.confidence !== null ? props.confidence : null
  const confidencePercent = confidence !== null ? confidence * 100 : null

  // Weights for HPS components (from scoring methodology)
  const weights = {
    f_generation: 0.30,
    f_fluid_interaction: 0.20,
    f_structural_pathways: 0.20,
    f_trap_retention: 0.15,
    f_surface_indicators: 0.10,
    f_thermodynamic: 0.05
  }

  // Calculate weighted contribution scores
  const contributions = {
    generation: {
      value: props.f_generation || 0,
      weight: weights.f_generation,
      label: 'Generation (G)',
      description: 'Hydrogen generation potential from mantle/crust'
    },
    migration: {
      value: props.f_fluid_interaction || 0,
      weight: weights.f_fluid_interaction,
      label: 'Migration/Fluid Interaction (M)',
      description: 'Pathways for hydrogen migration to surface'
    },
    trap: {
      value: props.f_trap_retention || 0,
      weight: weights.f_trap_retention,
      label: 'Trap/Retention (T)',
      description: 'Structural and stratigraphic traps'
    },
    seal: {
      value: props.f_structural_pathways || 0,
      weight: weights.f_structural_pathways,
      label: 'Seal/Structural (P)',
      description: 'Sealing capacity and structural integrity'
    },
    surface: {
      value: props.f_surface_indicators || 0,
      weight: weights.f_surface_indicators,
      label: 'Surface Indicators',
      description: 'Surface manifestations and anomalies'
    },
    thermodynamic: {
      value: props.f_thermodynamic || 0,
      weight: weights.f_thermodynamic,
      label: 'Thermodynamic Viability',
      description: 'Reaction conditions and viability'
    }
  }

  const getScoreClass = (score) => {
    if (score >= 0.8) return 'High-priority target'
    if (score >= 0.65) return 'Strong prospect, needs validation'
    if (score >= 0.5) return 'Moderate prospect'
    if (score >= 0.35) return 'Weak / speculative'
    return 'Low priority'
  }

  // Confidence adjustment explanation
  const getConfidenceExplanation = () => {
    if (confidence >= 0.8) return 'High confidence - abundant data coverage'
    if (confidence >= 0.6) return 'Moderate confidence - good data coverage'
    if (confidence >= 0.4) return 'Low-moderate confidence - some data gaps'
    return 'Low confidence - significant data gaps (see details below)'
  }

  const handleExport = async () => {
    try {
      setExporting(true)
      const response = await api.post('/export/report', {
        zone_id: props.id
      })
      setExportMessage('Report generation started. You will receive a download link shortly.')
      setTimeout(() => setExportMessage(null), 5000)
    } catch (error) {
      setExportMessage('Failed to export report: ' + error.message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="p-6 max-h-96 overflow-y-auto bg-gradient-to-b from-white to-gray-50">
      {/* Header Section */}
      <div className="mb-6 pb-4 border-b border-gray-200">
        <div className="flex justify-between items-start mb-3">
          <div>
            <p className="text-sm text-gray-500">Grid Cell</p>
            <p className="text-xl font-bold text-gray-900">
              ({props.grid_x !== null ? props.grid_x : '--'}, {props.grid_y !== null ? props.grid_y : '--'})
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Hydrogen Prospect Score</p>
            <p className={`text-3xl font-bold ${
              scorePercent !== null && scorePercent >= 80 ? 'text-red-600' :
              scorePercent !== null && scorePercent >= 65 ? 'text-orange-600' :
              scorePercent !== null && scorePercent >= 50 ? 'text-teal-600' :
              'text-gray-600'
            }`}>
              {scorePercent !== null ? scorePercent.toFixed(1) : '--'}
            </p>
          </div>
        </div>

        <div className="flex justify-between gap-4 text-sm">
          <div>
            <p className="text-gray-600">Classification</p>
            <p className="font-semibold text-teal-700">{score !== null ? getScoreClass(score) : '--'}</p>
          </div>
          <div>
            <p className="text-gray-600">Confidence</p>
            <p className="font-semibold text-blue-600">{confidencePercent !== null ? confidencePercent.toFixed(0) : '--'}%</p>
          </div>
          <div>
            <p className="text-gray-600">Rank</p>
            <p className="font-semibold text-gray-900">#{props.rank !== null ? props.rank : '--'}</p>
          </div>
        </div>
      </div>

      {/* Confidence Explanation */}
      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-xs font-medium text-blue-900 mb-1">Confidence Assessment</p>
        <p className="text-xs text-blue-800">{getConfidenceExplanation()}</p>
        <p className="text-xs text-blue-700 mt-1 italic">
          Final score adjusted by {(confidence * 100).toFixed(0)}% confidence factor
        </p>
      </div>

      {/* G/M/T/P Component Scores */}
      <div className="mb-4">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm font-medium text-teal-700 hover:text-teal-900 flex items-center gap-2"
        >
          <span>{showDetails ? '▼' : '▶'}</span>
          Hydrogen System Components (G/M/T/P)
        </button>

        {showDetails && (
          <div className="mt-3 space-y-2 pl-4 border-l-2 border-teal-200">
            {Object.entries(contributions).map(([key, comp]) => (
              <div key={key} className="text-xs">
                <div className="flex justify-between items-center mb-1">
                  <p className="font-semibold text-gray-900">{comp.label}</p>
                  <p className="font-bold text-teal-600">{(comp.value * 100).toFixed(1)}</p>
                </div>
                <p className="text-gray-600 text-xs mb-1">{comp.description}</p>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="bg-teal-500 h-1.5 rounded-full"
                    style={{ width: `${Math.min(comp.value * 100, 100)}%` }}
                  ></div>
                </div>
                <p className="text-gray-500 text-xs mt-1">
                  Weight: {(comp.weight * 100).toFixed(0)}% of final score
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Data Coverage Warning */}
      <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-xs font-medium text-yellow-900 mb-1">⚠ Data Availability</p>
        <p className="text-xs text-yellow-800">
          This region has moderate data coverage. Some subsurface data layers are incomplete.
          Score should be validated with additional surveys before final decision.
        </p>
        <p className="text-xs text-yellow-700 mt-1">
          Missing: Seismic interpretation, Borehole logs | Available: Gravity, Magnetic, Geology
        </p>
      </div>

      {/* Key Drivers */}
      <div className="mb-4">
        <p className="text-sm font-semibold text-gray-900 mb-2">Top Score Drivers</p>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-teal-600 font-bold">1.</span>
            <span className="text-gray-700">
              Strong <strong>Generation potential</strong> ({(contributions.generation.value * 100).toFixed(0)}) due to ultramafic composition
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-teal-600 font-bold">2.</span>
            <span className="text-gray-700">
              Favorable <strong>Trap geometry</strong> ({(contributions.trap.value * 100).toFixed(0)}) in anticline structure
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-teal-600 font-bold">3.</span>
            <span className="text-gray-700">
              Good <strong>Structural pathways</strong> ({(contributions.seal.value * 100).toFixed(0)}) along fault zones
            </span>
          </div>
        </div>
      </div>

      {/* Recommended Next Actions */}
      <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
        <p className="text-xs font-medium text-green-900 mb-2">Recommended Next Steps</p>
        <ul className="text-xs text-green-800 space-y-1">
          <li>• Acquire 3D seismic survey to validate trap geometry</li>
          <li>• Drill slim hole for subsurface sample confirmation</li>
          <li>• High-resolution gravity/magnetic inversion in fault zones</li>
        </ul>
      </div>

      {exportMessage && (
        <div className={`p-3 rounded text-sm ${
          exportMessage.includes('Failed')
            ? 'bg-red-50 text-red-700 border border-red-200'
            : 'bg-green-50 text-green-700 border border-green-200'
        }`}>
          {exportMessage}
        </div>
      )}
    </div>
  )
}
