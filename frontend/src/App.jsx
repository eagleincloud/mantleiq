import React, { useState, useEffect } from 'react'
import BasinSelector from './components/BasinSelector'
import MapView from './components/MapView'
import RankingList from './components/RankingList'
import ZonePanel from './components/ZonePanel'
import CompareTargets from './components/CompareTargets'
import ExecutiveBriefing from './components/ExecutiveBriefing'
import api from './services/api'

export default function App() {
  const [basins, setBasins] = useState([])
  const [selectedBasin, setSelectedBasin] = useState(null)
  const [zones, setZones] = useState([])
  const [selectedZone, setSelectedZone] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [gridType, setGridType] = useState('polygon')

  useEffect(() => {
    fetchBasins()
  }, [])

  const fetchBasins = async () => {
    try {
      setLoading(true)
      const response = await api.get('/basins')
      setBasins(Array.isArray(response.data) ? response.data : response.data.basins || [])
    } catch (err) {
      setError('Failed to load basins: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleBasinSelect = async (basin) => {
    setSelectedBasin(basin)
    setSelectedZone(null)
    setGridType('polygon')
    fetchGridData(basin, 'polygon')
  }

  const fetchGridData = async (basin, gridType) => {
    try {
      setLoading(true)
      const endpoint = gridType === 'h3'
        ? `/api/grids/h3/${basin.id}`
        : `/api/grids/polygon/${basin.id}`
      const response = await api.get(endpoint)
      const features = response.data.features || []
      setZones(features)
      setGridType(gridType)
    } catch (err) {
      setError(`Failed to load ${gridType} grid: ` + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleGridSwitch = (newGridType) => {
    if (selectedBasin) {
      fetchGridData(selectedBasin, newGridType)
    }
  }

  const handleZoneSelect = (zone) => {
    setSelectedZone(zone)
  }

  const [showCompare, setShowCompare] = useState(false)
  const [showBriefing, setShowBriefing] = useState(false)

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-96 bg-white border-r border-gray-200 shadow-sm overflow-y-auto">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-teal-700 mb-2">MantleIQ</h1>
          <p className="text-sm text-gray-600 mb-6">Natural Hydrogen Prospectivity Analysis</p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-sm text-red-700">
              {error}
            </div>
          )}

          <BasinSelector
            basins={basins}
            selectedBasin={selectedBasin}
            onSelect={handleBasinSelect}
            loading={loading}
          />

          {selectedBasin && (
            <>
              <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-xs font-semibold text-gray-700 mb-2">Grid Type</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleGridSwitch('polygon')}
                    className={`flex-1 px-3 py-2 rounded text-sm font-medium transition ${
                      gridType === 'polygon'
                        ? 'bg-teal-600 text-white'
                        : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                    disabled={loading}
                  >
                    Polygon ({zones.length})
                  </button>
                  <button
                    onClick={() => handleGridSwitch('h3')}
                    className={`flex-1 px-3 py-2 rounded text-sm font-medium transition ${
                      gridType === 'h3'
                        ? 'bg-teal-600 text-white'
                        : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                    disabled={loading}
                  >
                    H3 ({zones.length})
                  </button>
                </div>
              </div>
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Prospect Zones</h2>
                <RankingList
                  zones={zones}
                  selectedZone={selectedZone}
                  onSelect={handleZoneSelect}
                  loading={loading}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {selectedBasin ? (
          <>
            <MapView basin={selectedBasin} zones={zones} selectedZone={selectedZone} />
            {selectedZone && (
              <div className="border-t border-gray-200 bg-white shadow-sm">
                <div className="flex gap-2 p-4 border-b border-gray-200">
                  <button
                    onClick={() => setShowBriefing(true)}
                    className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                  >
                    📋 Executive Briefing
                  </button>
                  <button
                    onClick={() => setShowCompare(true)}
                    className="flex-1 px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium"
                  >
                    ⚖️ Compare Targets
                  </button>
                </div>
                <ZonePanel zone={selectedZone} />
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center h-full bg-gray-100">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Select a Basin</h2>
              <p className="text-gray-600">Choose a basin from the left panel to get started</p>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showBriefing && selectedZone && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-lg w-full max-w-5xl max-h-screen flex flex-col">
            <div className="flex justify-end p-4 border-b border-gray-200">
              <button
                onClick={() => setShowBriefing(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ✕
              </button>
            </div>
            <ExecutiveBriefing zone={selectedZone} basin={selectedBasin} />
          </div>
        </div>
      )}

      {showCompare && (
        <CompareTargets zones={zones} onClose={() => setShowCompare(false)} />
      )}
    </div>
  )
}
