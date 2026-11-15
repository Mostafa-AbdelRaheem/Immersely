// src/features/auth/tokenFromHash.js
// Reads a one-time token from a URL fragment such as "#token=abc".
// Browsers never send the fragment to a server, so the token stays out of
// server logs and Referer headers. Pure: takes the hash as an argument.

export function readTokenFromHash(hash) {
  if (typeof hash !== 'string') return null
  const params = new URLSearchParams(hash.startsWith('#') ? hash.slice(1) : hash)
  const token = params.get('token')?.trim()
  return token ? token : null
}