// Format utilities for displaying data with missing value indicators

export const formatScore = (score, decimals = 1) => {
  if (score === null || score === undefined || isNaN(score)) {
    return '--'
  }
  return (score * 100).toFixed(decimals)
}

export const formatPercent = (value, decimals = 0) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '--'
  }
  return (value * 100).toFixed(decimals)
}

export const formatNumber = (value, decimals = 2) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '--'
  }
  return value.toFixed(decimals)
}

export const formatText = (value) => {
  if (value === null || value === undefined || value === '' || value === 'null') {
    return '--'
  }
  return String(value)
}

export const formatCoordinate = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '--'
  }
  return value.toFixed(4)
}

export const formatRank = (rank, index) => {
  if (rank === null || rank === undefined) {
    return `#${index + 1}`
  }
  return `#${rank}`
}
