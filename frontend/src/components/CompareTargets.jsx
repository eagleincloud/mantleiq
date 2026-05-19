import React, { useState } from 'react'
import { formatScore, formatPercent } from '../utils/formatters'

export default function CompareTargets({ zones, onClose }) {
  const [selectedZones, setSelectedZones] = useState([])
  const [showComparison, setShowComparison] = useState(false)

  const toggleZoneSelection = (zone) => {
    if (selectedZones.some(z => z.properties.id === zone.properties.id)) {
      setSelectedZones(selectedZones.filter(z => z.properties.id !== zone.properties.id))
    } else {
      if (selectedZones.length < 3) {
        setSelectedZones([...selectedZones, zone])
      }
    }
  }

  const handleExportComparison = () => {
    const csv = generateComparisonCSV()
    downloadCSV(csv, 'zone-comparison.csv')
  }

  const generateComparisonCSV = () => {
    let csv = 'Grid Cell,Prospectivity Score,Confidence,Rank,Classification,Generation,Migration,Trap,Seal\n'
    selectedZones.forEach(zone => {
      const props = zone.properties || {}
      const score = props.prospectivity_score !== null ? formatScore(props.prospectivity_score, 1) : '--'
      const confidence = props.confidence !== null ? formatPercent(props.confidence, 0) : '--'
      const generation = props.f_generation !== null ? formatPercent(props.f_generation, 0) : '--'
      const migration = props.f_fluid_interaction !== null ? formatPercent(props.f_fluid_interaction, 0) : '--'
      const trap = props.f_trap_retention !== null ? formatPercent(props.f_trap_retention, 0) : '--'
      const seal = props.f_structural_pathways !== null ? formatPercent(props.f_structural_pathways, 0) : '--'
      csv += `"(${props.grid_x},${props.grid_y})","${score}","${confidence}%","${props.rank}","${props.score_class}","${generation}","${migration}","${trap}","${seal}"\n`
    })
    return csv
  }

  const downloadCSV = (csv, filename) => {
    const link = document.createElement('a')
    link.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv)
    link.download = filename
    link.click()
  }

  if (!showComparison) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full max-h-96 flex flex-col">
          <div className="flex justify-between items-center p-6 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">Compare Targets</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            <p className="text-sm text-gray-600 mb-4">
              Select up to 3 cells to compare side-by-side (currently {selectedZones.length}/3)
            </p>

            <div className="space-y-2">
              {zones.slice(0, 20).map(zone => {
                const props = zone.properties || {}
                const isSelected = selectedZones.some(z => z.properties.id === props.id)
                const score = props.prospectivity_score !== null ? props.prospectivity_score * 100 : null
                const displayScore = score !== null ? score.toFixed(0) : '--'
                const confidence = props.confidence !== null ? props.confidence * 100 : null
                const displayConfidence = confidence !== null ? confidence.toFixed(0) : '--'

                return (
                  <button
                    key={props.id}
                    onClick={() => toggleZoneSelection(zone)}
                    className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                      isSelected
                        ? 'border-teal-500 bg-teal-50'
                        : 'border-gray-200 bg-white hover:border-teal-300'
                    } ${selectedZones.length >= 3 && !isSelected ? 'opacity-50 cursor-not-allowed' : ''}`}
                    disabled={selectedZones.length >= 3 && !isSelected}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">
                          Cell ({props.grid_x}, {props.grid_y})
                        </p>
                        <p className="text-sm text-gray-600">
                          Rank #{props.rank} | Confidence {displayConfidence}%
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-teal-600">{displayScore}</p>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}}
                          className="mt-1"
                        />
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="flex justify-end gap-2 p-6 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => setShowComparison(true)}
              disabled={selectedZones.length === 0}
              className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50"
            >
              Compare Selected ({selectedZones.length})
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Comparison view
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-5xl max-h-96 flex flex-col">
        <div className="flex justify-between items-center p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Target Comparison</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-x-auto p-6">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-100">
              <tr>
                <th className="text-left p-2 border border-gray-300">Metric</th>
                {selectedZones.map((zone, idx) => {
                  const props = zone.properties || {}
                  return (
                    <th key={idx} className="text-center p-2 border border-gray-300 bg-teal-50">
                      <p className="font-bold text-teal-900">({props.grid_x}, {props.grid_y})</p>
                      <p className="text-xs text-teal-700">#{props.rank}</p>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              <tr className="hover:bg-gray-50">
                <td className="p-2 border border-gray-300 font-bold">Prospectivity Score</td>
                {selectedZones.map((zone, idx) => {
                  const props = zone.properties || {}
                  const score = props.prospectivity_score !== null ? props.prospectivity_score * 100 : null
                  const displayScore = score !== null ? score.toFixed(1) : '--'
                  return (
                    <td key={idx} className="text-center p-2 border border-gray-300">
                      <p className={`text-lg font-bold ${
                        score !== null && score >= 80 ? 'text-red-600' :
                        score !== null && score >= 65 ? 'text-orange-600' :
                        score !== null && score >= 50 ? 'text-teal-600' :
                        'text-gray-600'
                      }`}>
                        {displayScore}
                      </p>
                    </td>
                  )
                })}
              </tr>
              <tr className="bg-gray-50">
                <td className="p-2 border border-gray-300 font-bold">Confidence</td>
                {selectedZones.map((zone, idx) => {
                  const props = zone.properties || {}
                  const confidence = props.confidence !== null ? props.confidence * 100 : null
                  const displayConfidence = confidence !== null ? confidence.toFixed(0) : '--'
                  return (
                    <td key={idx} className="text-center p-2 border border-gray-300">
                      <p className="font-semibold text-blue-600">
                        {displayConfidence}%
                      </p>
                    </td>
                  )
                })}
              </tr>
              <tr className="hover:bg-gray-50">
                <td className="p-2 border border-gray-300 font-bold">Classification</td>
                {selectedZones.map((zone, idx) => {
                  const props = zone.properties || {}
                  return (
                    <td key={idx} className="text-center p-2 border border-gray-300">
                      <p className="text-xs font-semibold text-gray-700">{props.score_class || '--'}</p>
                    </td>
                  )
                })}
              </tr>
              <tr className="bg-gray-50 font-bold">
                <td className="p-2 border border-gray-300">Generation (G)</td>
                {selectedZones.map((zone, idx) => {
                  const props = zone.properties || {}
                  const generation = props.f_generation !== null ? (props.f_generation * 100).toFixed(0) : '--'
                  return (
                    <td key={idx} className="text-center p-2 border border-gray-300">
                      {generation}
                    </td>
                  )
                })}
              </tr>
              <tr className="hover:bg-gray-50 font-bold">
                <td className="p-2 border border-gray-300">Migration (M)</td>
                {selectedZones.map((zone, idx) => {
                  const props = zone.properties || {}
                  const migration = props.f_fluid_interaction !== null ? (props.f_fluid_interaction * 100).toFixed(0) : '--'
                  return (
                    <td key={idx} className="text-center p-2 border border-gray-300">
                      {migration}
                    </td>
                  )
                })}
              </tr>
              <tr className="bg-gray-50 font-bold">
                <td className="p-2 border border-gray-300">Trap (T)</td>
                {selectedZones.map((zone, idx) => {
                  const props = zone.properties || {}
                  const trap = props.f_trap_retention !== null ? (props.f_trap_retention * 100).toFixed(0) : '--'
                  return (
                    <td key={idx} className="text-center p-2 border border-gray-300">
                      {trap}
                    </td>
                  )
                })}
              </tr>
              <tr className="hover:bg-gray-50 font-bold">
                <td className="p-2 border border-gray-300">Seal/Structural (P)</td>
                {selectedZones.map((zone, idx) => {
                  const props = zone.properties || {}
                  const seal = props.f_structural_pathways !== null ? (props.f_structural_pathways * 100).toFixed(0) : '--'
                  return (
                    <td key={idx} className="text-center p-2 border border-gray-300">
                      {seal}
                    </td>
                  )
                })}
              </tr>
            </tbody>
          </table>
        </div>

        <div className="flex justify-end gap-2 p-6 border-t border-gray-200">
          <button
            onClick={() => setShowComparison(false)}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Back to Selection
          </button>
          <button
            onClick={handleExportComparison}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            📥 Export as CSV
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
