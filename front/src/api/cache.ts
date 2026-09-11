// Frontend Cache System - Cache en cliente usando localStorage con TTL
// https://github.com/med-appointments

// Cache map for in-memory storage
const cache: Map<string, { data: any; timestamp: number; ttl: number }> = new Map();

// Time to live defaults (in minutes)
const DEFAULT_TTL: number = 5;

/**
 * Set cache entry with TTL
 * @param key - Cache key
 * @param data - Data to cache
 * @param ttl - Time to live in minutes (default: 5)
 */
function setCache(key: string, data: any, ttl: number = DEFAULT_TTL): void {
  const entry = {
    data,
    timestamp: Date.now(),
    ttl,
  };
  
  // Guardar en localStorage
  localStorage.setItem(`cache_${key}`, JSON.stringify(entry));
  
  // Actualizar en memoria
  cache.set(key, entry);
}

/**
 * Get cached data if still valid
 * @param key - Cache key
 * @param ttl - Time to live in minutes (default: 5)
 * @returns Cached data or null if expired/invalid
 */
function getCache<T>(key: string, ttl: number = DEFAULT_TTL): T | null {
  const cachedEntry = localStorage.getItem(`cache_${key}`);
  
  if (!cachedEntry) {
    return null;
  }
  
  try {
    const data = JSON.parse(cachedEntry as string);
    
    // Check if cached data is still valid
    const age = Date.now() - data.timestamp;
    if (age > ttl * 60 * 1000) {
      // Expirado, remover y retornar null
      localStorage.removeItem(`cache_${key}`);
      return null;
    }
    
    return data as T;
  } catch (error) {
    console.error('Error parsing cached data:', error);
    localStorage.removeItem(`cache_${key}`);
    return null;
  }
}

/**
 * Invalidate specific cache entry
 * @param key - Cache key to invalidate
 */
function invalidateCache(key: string): void {
  localStorage.removeItem(`cache_${key}`);
  cache.delete(key);
}

/**
 * Invalidate all caches
 */
function invalidateAllCaches(): void {
  localStorage.clear();
  cache.clear();
}

/**
 * Get cache size (entries count)
 * @returns Number of cached entries
 */
function getCacheSize(): number {
  return cache.size;
}

/**
 * Clean expired entries from cache
 */
function cleanupCaches(): void {
  const now = Date.now();
  cache.forEach((entry, key) => {
    if (now - entry.timestamp > entry.ttl * 60 * 1000) {
      localStorage.removeItem(`cache_${key}`);
      cache.delete(key);
    }
  });
}

// Export all functions as cacheApi object
export const cacheApi = {
  setCache,
  getCache,
  invalidateCache,
  invalidateAllCaches,
  getCacheSize,
  cleanupCaches,
};