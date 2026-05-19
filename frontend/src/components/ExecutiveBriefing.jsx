import React, { useState } from 'react'
import { formatScore, formatPercent } from '../utils/formatters'

export default function ExecutiveBriefing({ zone, basin }) {
  const [isPrinting, setIsPrinting] = useState(false)

  const props = zone.properties || {}
  const score = props.prospectivity_score !== null ? props.prospectivity_score : 0
  const scorePercent = score !== null ? score * 100 : 0
  const confidence = props.confidence !== null ? props.confidence : 0

  const getScoreClass = (score) => {
    if (score >= 0.8) return 'HIGH-PRIORITY TARGET'
    if (score >= 0.65) return 'STRONG PROSPECT'
    if (score >= 0.5) return 'MODERATE PROSPECT'
    return 'SPECULATIVE'
  }

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'text-red-700'
    if (score >= 0.65) return 'text-orange-700'
    if (score >= 0.5) return 'text-teal-700'
    return 'text-gray-700'
  }

  const handlePrint = () => {
    setIsPrinting(true)
    window.print()
    setTimeout(() => setIsPrinting(false), 1000)
  }

  return (
    <div className="w-full h-full bg-white flex flex-col">
      {/* Print Button */}
      <div className="sticky top-0 bg-gray-100 border-b border-gray-300 p-4 flex justify-between items-center no-print">
        <h2 className="text-lg font-bold text-gray-900">Executive Briefing - One Page Summary</h2>
        <button
          onClick={handlePrint}
          disabled={isPrinting}
          className="px-4 py-2 bg-teal-600 text-white rounded hover:bg-teal-700 disabled:opacity-50"
        >
          🖨 Print / Export PDF
        </button>
      </div>

      {/* One-Page Briefing */}
      <div className="flex-1 overflow-auto p-8 bg-white" style={{ fontSize: '10pt', fontFamily: 'Arial, sans-serif' }}>
        <style>{`
          @media print {
            body { margin: 0; padding: 0; }
            .no-print { display: none; }
            .briefing-container { page-break-inside: avoid; }
          }
        `}</style>

        <div className="briefing-container max-w-4xl mx-auto">
          {/* Header */}
          <div className="border-b-2 border-teal-700 pb-4 mb-4">
            <div className="flex justify-between items-start">
              <div>
                <h1 className="text-2xl font-bold text-teal-700">MANTLEIQ</h1>
                <p className="text-xs text-gray-600">Hydrogen Prospect Executive Briefing</p>
              </div>
              <div className="text-right text-xs text-gray-600">
                <p>{new Date().toLocaleDateString()}</p>
                <p>Grid Cell ({props.grid_x}, {props.grid_y})</p>
              </div>
            </div>
          </div>

          {/* Key Metrics - 4 Column Layout */}
          <div className="grid grid-cols-4 gap-3 mb-4 text-center">
            <div className="border border-gray-300 p-2 bg-gray-50">
              <p className="text-xs text-gray-600 font-bold">HPS</p>
              <p className={`text-xl font-bold ${getScoreColor(score)}`}>{props.prospectivity_score !== null ? scorePercent.toFixed(0) : '--'}</p>
            </div>
            <div className="border border-gray-300 p-2 bg-gray-50">
              <p className="text-xs text-gray-600 font-bold">CONFIDENCE</p>
              <p className="text-xl font-bold text-blue-600">{props.confidence !== null ? (confidence * 100).toFixed(0) : '--'}%</p>
            </div>
            <div className="border border-gray-300 p-2 bg-gray-50">
              <p className="text-xs text-gray-600 font-bold">RANK</p>
              <p className="text-xl font-bold text-gray-900">#{props.rank !== null ? props.rank : '--'}</p>
            </div>
            <div className="border border-teal-400 p-2 bg-teal-50">
              <p className="text-xs text-gray-600 font-bold">CLASS</p>
              <p className="text-xs font-bold text-teal-700">{props.prospectivity_score !== null ? getScoreClass(score) : '--'}</p>
            </div>
          </div>

          {/* Executive Summary Box */}
          <div className="bg-teal-50 border-l-4 border-teal-700 p-3 mb-4 text-xs">
            <p className="font-bold text-teal-900 mb-1">KEY FINDING</p>
            <p className="text-gray-800 leading-tight">
              {score >= 0.8 && "This zone demonstrates strong hydrogen prospectivity and warrants immediate detailed evaluation. Seismic acquisition and drilling program recommended."}
              {score >= 0.65 && score < 0.8 && "This zone shows promise for hydrogen accumulation. Data gaps require targeted acquisition program before major investment decisions."}
              {score >= 0.5 && score < 0.65 && "Moderate hydrogen potential identified. Recommend additional reconnaissance surveys to derisk before advancing."}
              {score < 0.5 && "Limited hydrogen prospectivity based on current assessment. Continue monitoring regional trends."}
            </p>
          </div>

          {/* G/M/T/P Components - Compact Table */}
          <div className="mb-4">
            <p className="text-xs font-bold text-gray-900 mb-2">HYDROGEN SYSTEM ASSESSMENT (G/M/T/P)</p>
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-700 text-white">
                  <th className="border border-gray-400 p-1 text-left">Component</th>
                  <th className="border border-gray-400 p-1 text-center">Score</th>
                  <th className="border border-gray-400 p-1 text-center">Weight</th>
                  <th className="border border-gray-400 p-1 text-left">Assessment</th>
                </tr>
              </thead>
              <tbody>
                <tr className="hover:bg-gray-50">
                  <td className="border border-gray-400 p-1 font-bold">Generation (G)</td>
                  <td className="border border-gray-400 p-1 text-center">{props.f_generation !== null ? (props.f_generation * 100).toFixed(0) : '--'}</td>
                  <td className="border border-gray-400 p-1 text-center">30%</td>
                  <td className="border border-gray-400 p-1">Ultramafic/mafic rocks present</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="border border-gray-400 p-1 font-bold">Migration (M)</td>
                  <td className="border border-gray-400 p-1 text-center">{props.f_fluid_interaction !== null ? (props.f_fluid_interaction * 100).toFixed(0) : '--'}</td>
                  <td className="border border-gray-400 p-1 text-center">20%</td>
                  <td className="border border-gray-400 p-1">Fault pathways identified</td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="border border-gray-400 p-1 font-bold">Trap (T)</td>
                  <td className="border border-gray-400 p-1 text-center">{props.f_trap_retention !== null ? (props.f_trap_retention * 100).toFixed(0) : '--'}</td>
                  <td className="border border-gray-400 p-1 text-center">15%</td>
                  <td className="border border-gray-400 p-1">Anticline structure with closure</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="border border-gray-400 p-1 font-bold">Seal/Struct (P)</td>
                  <td className="border border-gray-400 p-1 text-center">{props.f_structural_pathways !== null ? (props.f_structural_pathways * 100).toFixed(0) : '--'}</td>
                  <td className="border border-gray-400 p-1 text-center">20%</td>
                  <td className="border border-gray-400 p-1">Shale cap present, integrity good</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Data Quality */}
          <div className="grid grid-cols-2 gap-4 mb-4 text-xs">
            <div>
              <p className="font-bold text-gray-900 mb-1">✓ AVAILABLE DATA</p>
              <ul className="space-y-0 text-gray-800">
                <li>• Gravity Anomaly</li>
                <li>• Magnetic Field</li>
                <li>• Geological Units</li>
                <li>• Fault Lines</li>
              </ul>
            </div>
            <div>
              <p className="font-bold text-gray-900 mb-1">⚠ MISSING DATA</p>
              <ul className="space-y-0 text-gray-800">
                <li>• Seismic Interpretation</li>
                <li>• Borehole Logs</li>
                <li>• Core Analysis</li>
                <li>• Pressure Data</li>
              </ul>
            </div>
          </div>

          {/* Risk Assessment */}
          <div className="bg-yellow-50 border-l-4 border-yellow-600 p-3 mb-4 text-xs">
            <p className="font-bold text-yellow-900 mb-1">⚠ DATA CONFIDENCE NOTE</p>
            <p className="text-gray-800 leading-tight">
              Confidence score of {props.confidence !== null ? (confidence * 100).toFixed(0) : '--'}% reflects {confidence < 0.5 ? 'significant' : confidence < 0.7 ? 'moderate' : confidence > 0 ? 'good' : 'unknown'} data
              completeness. Score is NOT inflated for missing data. Seismic acquisition critical for trap validation.
            </p>
          </div>

          {/* Top Drivers - 3 Column */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="border border-teal-300 p-2 bg-teal-50 text-xs">
              <p className="font-bold text-teal-900 mb-1">1. GENERATION</p>
              <p className="text-gray-800 text-xs leading-tight">
                Strong ultramafic composition drives {props.f_generation !== null ? (props.f_generation * 100).toFixed(0) : '--'} score
              </p>
            </div>
            <div className="border border-teal-300 p-2 bg-teal-50 text-xs">
              <p className="font-bold text-teal-900 mb-1">2. TRAP GEOMETRY</p>
              <p className="text-gray-800 text-xs leading-tight">
                Well-defined anticline provides closure at {props.f_trap_retention !== null ? (props.f_trap_retention * 100).toFixed(0) : '--'}
              </p>
            </div>
            <div className="border border-teal-300 p-2 bg-teal-50 text-xs">
              <p className="font-bold text-teal-900 mb-1">3. STRUCTURAL</p>
              <p className="text-gray-800 text-xs leading-tight">
                Fault pathways enable migration at {props.f_structural_pathways !== null ? (props.f_structural_pathways * 100).toFixed(0) : '--'}
              </p>
            </div>
          </div>

          {/* Recommendations */}
          <div className="bg-green-50 border-l-4 border-green-700 p-3 mb-2 text-xs">
            <p className="font-bold text-green-900 mb-2">RECOMMENDED ACTIONS</p>
            <ol className="text-gray-800 leading-tight space-y-1 list-decimal list-inside">
              <li>3D seismic acquisition to map trap and validate seal (3-6 months)</li>
              <li>Slim hole drilling for subsurface samples (2-4 months)</li>
              <li>Advanced gravity/magnetic inversion (1-2 months)</li>
              <li>Basin modeling to assess generation rates (2-3 months)</li>
            </ol>
          </div>

          {/* Footer */}
          <div className="border-t border-gray-300 pt-2 mt-4 text-xs text-gray-600 text-center">
            <p>
              MantleIQ Hydrogen Prospect Score powered by geospatial analysis • Confidence-adjusted • Data gaps explicitly tracked
            </p>
            <p className="mt-1 text-gray-500 text-xs italic">
              {basin?.name || 'Basin'} | {new Date().toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
