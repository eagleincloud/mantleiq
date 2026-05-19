import React from 'react'

export default function BasinSelector({ basins, selectedBasin, onSelect, loading }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Select Basin
      </label>
      <select
        value={selectedBasin?.id || ''}
        onChange={(e) => {
          const basin = basins.find(b => b.id === e.target.value)
          if (basin) onSelect(basin)
        }}
        disabled={loading}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:opacity-50"
      >
        <option value="">Choose a basin...</option>
        {basins.map(basin => (
          <option key={basin.id} value={basin.id}>
            {basin.name} {basin.region && `(${basin.region})`}
          </option>
        ))}
      </select>
      {selectedBasin && (
        <div className="mt-3 p-3 bg-teal-50 border border-teal-200 rounded">
          <p className="text-sm font-medium text-teal-900">{selectedBasin.name}</p>
          {selectedBasin.region && (
            <p className="text-xs text-teal-700 mt-1">{selectedBasin.region}</p>
          )}
          {selectedBasin.description && (
            <p className="text-xs text-gray-600 mt-2">{selectedBasin.description}</p>
          )}
        </div>
      )}
    </div>
  )
}
