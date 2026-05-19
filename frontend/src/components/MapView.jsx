import React, { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'

export default function MapView({ basin, zones, selectedZone }) {
  const mapContainer = useRef(null)
  const map = useRef(null)

  useEffect(() => {
    if (!mapContainer.current) return

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [-95, 35],
      zoom: 4
    })

    return () => map.current?.remove()
  }, [])

  useEffect(() => {
    if (!map.current || !zones || zones.length === 0) return

    const geojsonData = {
      type: 'FeatureCollection',
      features: zones
    }

    if (!map.current.getSource('tiles')) {
      map.current.addSource('tiles', {
        type: 'geojson',
        data: geojsonData
      })

      // Main tile fill layer
      map.current.addLayer({
        id: 'tiles-fill',
        type: 'fill',
        source: 'tiles',
        paint: {
          'fill-color': [
            'interpolate',
            ['linear'],
            ['get', 'prospectivity_score'],
            0, '#1a4d7a',      // Deep blue
            0.2, '#2c6ba5',    // Blue
            0.4, '#5ba3d0',    // Light blue
            0.5, '#d4a574',    // Yellow-orange
            0.65, '#e8943d',   // Orange
            0.8, '#d94848',    // Red-orange
            1.0, '#8b0000'     // Dark red
          ],
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.9,
            0.7
          ]
        }
      })

      // Outline layer
      map.current.addLayer({
        id: 'tiles-outline',
        type: 'line',
        source: 'tiles',
        paint: {
          'line-color': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            '#000',
            '#333'
          ],
          'line-width': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            3,
            1
          ],
          'line-opacity': 0.7
        }
      })


      let hoveredId = null

      map.current.on('mousemove', 'tiles-fill', (e) => {
        if (e.features.length > 0) {
          if (hoveredId !== null) {
            map.current.setFeatureState(
              { source: 'tiles', id: hoveredId },
              { hover: false }
            )
          }
          hoveredId = e.features[0].id
          map.current.setFeatureState(
            { source: 'tiles', id: hoveredId },
            { hover: true }
          )
          map.current.getCanvas().style.cursor = 'pointer'
        }
      })

      map.current.on('mouseleave', 'tiles-fill', () => {
        if (hoveredId !== null) {
          map.current.setFeatureState(
            { source: 'tiles', id: hoveredId },
            { hover: false }
          )
        }
        hoveredId = null
        map.current.getCanvas().style.cursor = ''
      })

      map.current.on('click', 'tiles-fill', (e) => {
        if (e.features && e.features[0]) {
          const props = e.features[0].properties
          const score = props.prospectivity_score !== null ? props.prospectivity_score : null
          const confidence = props.confidence !== null ? props.confidence : null
          const scoreDisplay = score !== null ? (score * 100).toFixed(1) : '--'
          const confidenceDisplay = confidence !== null ? (confidence * 100).toFixed(0) : '--'
          const rankDisplay = props.rank !== null ? props.rank : '--'
          const gridXDisplay = props.grid_x !== null ? props.grid_x : '--'
          const gridYDisplay = props.grid_y !== null ? props.grid_y : '--'
          const hasDataGaps = confidence !== null && confidence < 0.5

          new maplibregl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(`
              <div class="font-sans">
                <strong>Score: ${scoreDisplay}</strong><br/>
                Confidence: ${confidenceDisplay}%<br/>
                Rank: #${rankDisplay}<br/>
                Grid: (${gridXDisplay}, ${gridYDisplay})
                ${hasDataGaps ? '<div style="margin-top: 8px; padding: 8px; background: #FFF3CD; border-radius: 4px; font-size: 11px; color: #856404;"><strong>⚠ Data gaps detected</strong><br/>Score confidence is reduced due to missing data layers.</div>' : ''}
              </div>
            `)
            .addTo(map.current)
        }
      })
    } else {
      map.current.getSource('tiles').setData(geojsonData)
    }
  }, [zones])

  return (
    <div ref={mapContainer} className="flex-1 relative">
      <div className="absolute top-4 left-4 bg-white p-4 rounded-lg shadow z-10 max-w-xs">
        <h3 className="font-semibold text-gray-900 mb-2">{basin?.name || 'Basin'}</h3>
        <div className="text-sm text-gray-600">
          <p>Total cells: <strong>{zones?.length || 0}</strong></p>

          <div className="mt-4 space-y-2">
            <p className="font-medium text-gray-900 text-xs">Prospectivity Score Heatmap</p>

            {/* Gradient bar */}
            <div className="w-full h-6 rounded" style={{
              background: 'linear-gradient(to right, #1a4d7a 0%, #2c6ba5 20%, #5ba3d0 40%, #d4a574 50%, #e8943d 65%, #d94848 80%, #8b0000 100%)'
            }}></div>

            <div className="flex justify-between text-xs text-gray-600">
              <span>0.0</span>
              <span>0.5</span>
              <span>1.0</span>
            </div>

            <div className="space-y-1 text-xs mt-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#1a4d7a' }}></div>
                <span>Very Low (0-0.2)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#5ba3d0' }}></div>
                <span>Low-Med (0.2-0.5)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#d4a574' }}></div>
                <span>Medium (0.5-0.65)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#e8943d' }}></div>
                <span>High (0.65-0.8)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#d94848' }}></div>
                <span>Very High (0.8-1.0)</span>
              </div>
            </div>

            </div>

          <p className="text-xs text-gray-500 mt-4 italic">
            Click on cells to see details
          </p>
        </div>
      </div>
    </div>
  )
}
