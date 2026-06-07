/**
 * API module for fetching items from backend.
 */
const API_BASE = '/api'

export async function fetchItems() {
  const response = await fetch(`${API_BASE}/items`)
  if (!response.ok) throw new Error('Failed to fetch items')
  return response.json()
}

export async function fetchItem(id) {
  const response = await fetch(`${API_BASE}/items/${id}`)
  if (!response.ok) throw new Error('Failed to fetch item')
  return response.json()
}

export async function createItem(data) {
  const response = await fetch(`${API_BASE}/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error('Failed to create item')
  return response.json()
}
