// PWA Offline-First Utilities
// This module enhances the e-wallet app with offline capabilities

class PWAStorage {
  constructor() {
    this.PRICE_CACHE = 'pwa_price_cache';
    this.PRICE_HISTORY_CACHE = 'pwa_price_history_cache';
    this.MINTS_CACHE = 'pwa_mints_cache';
    this.BALANCE_CACHE = 'pwa_balance_cache';
    this.TRANSACTIONS_CACHE = 'pwa_transactions_cache';
    this.CACHE_TIMESTAMPS = 'pwa_cache_timestamps';
    this.CACHE_DURATION = {
      price: 60000,           // 1 minute
      priceHistory: 3600000,  // 1 hour
      mints: 3600000,         // 1 hour
      balance: 30000,         // 30 seconds
      transactions: 60000     // 1 minute
    };
  }

  /**
   * Save data to offline cache with timestamp
   */
  save(cacheKey, data, duration = null) {
    try {
      const timestamps = this._getTimestamps();
      timestamps[cacheKey] = Date.now();
      localStorage.setItem(this.CACHE_TIMESTAMPS, JSON.stringify(timestamps));
      localStorage.setItem(cacheKey, JSON.stringify(data));
      return true;
    } catch (e) {
      console.warn('Failed to save to offline cache:', e);
      return false;
    }
  }

  /**
   * Get data from offline cache if still valid
   */
  get(cacheKey, duration) {
    try {
      const timestamps = this._getTimestamps();
      const timestamp = timestamps[cacheKey];
      const cacheDuration = duration || this.CACHE_DURATION[cacheKey] || 60000;

      if (!timestamp) return null;
      if (Date.now() - timestamp > cacheDuration) {
        this.remove(cacheKey);
        return null;
      }

      const data = localStorage.getItem(cacheKey);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.warn('Failed to read from offline cache:', e);
      return null;
    }
  }

  /**
   * Check if cached data is still fresh
   */
  isFresh(cacheKey, duration) {
    try {
      const timestamps = this._getTimestamps();
      const timestamp = timestamps[cacheKey];
      const cacheDuration = duration || this.CACHE_DURATION[cacheKey] || 60000;

      if (!timestamp) return false;
      return Date.now() - timestamp <= cacheDuration;
    } catch (e) {
      return false;
    }
  }

  /**
   * Remove specific cache entry
   */
  remove(cacheKey) {
    try {
      localStorage.removeItem(cacheKey);
      const timestamps = this._getTimestamps();
      delete timestamps[cacheKey];
      localStorage.setItem(this.CACHE_TIMESTAMPS, JSON.stringify(timestamps));
      return true;
    } catch (e) {
      console.warn('Failed to remove from offline cache:', e);
      return false;
    }
  }

  /**
   * Clear all offline cache
   */
  clearAll() {
    try {
      localStorage.removeItem(this.PRICE_CACHE);
      localStorage.removeItem(this.PRICE_HISTORY_CACHE);
      localStorage.removeItem(this.MINTS_CACHE);
      localStorage.removeItem(this.BALANCE_CACHE);
      localStorage.removeItem(this.TRANSACTIONS_CACHE);
      localStorage.removeItem(this.CACHE_TIMESTAMPS);
      return true;
    } catch (e) {
      console.warn('Failed to clear offline cache:', e);
      return false;
    }
  }

  _getTimestamps() {
    try {
      const timestamps = localStorage.getItem(this.CACHE_TIMESTAMPS);
      return timestamps ? JSON.parse(timestamps) : {};
    } catch (e) {
      return {};
    }
  }
}

// Initialize PWA storage
const pwaStorage = new PWAStorage();

/**
 * Enhanced fetch with offline fallback
 */
async function fetchWithOfflineFallback(url, options = {}) {
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    // Determine cache key based on URL
    let cacheKey;
    if (url.includes('/api/btc-price-history')) {
      cacheKey = pwaStorage.PRICE_HISTORY_CACHE;
    } else if (url.includes('/api/btc-price')) {
      cacheKey = pwaStorage.PRICE_CACHE;
    } else if (url.includes('/api/mints')) {
      cacheKey = pwaStorage.MINTS_CACHE;
    } else if (url.includes('/api/wallet/balance')) {
      cacheKey = pwaStorage.BALANCE_CACHE;
    } else if (url.includes('/api/transactions')) {
      cacheKey = pwaStorage.TRANSACTIONS_CACHE;
    }
    
    // Cache successful response
    if (cacheKey && data) {
      pwaStorage.save(cacheKey, data);
    }
    
    return { data, success: true, offline: false };
  } catch (error) {
    console.log('Network request failed, attempting offline fallback:', error);
    
    // Try to get from cache
    let cacheKey;
    if (url.includes('/api/btc-price-history')) {
      cacheKey = pwaStorage.PRICE_HISTORY_CACHE;
    } else if (url.includes('/api/btc-price')) {
      cacheKey = pwaStorage.PRICE_CACHE;
    } else if (url.includes('/api/mints')) {
      cacheKey = pwaStorage.MINTS_CACHE;
    } else if (url.includes('/api/wallet/balance')) {
      cacheKey = pwaStorage.BALANCE_CACHE;
    } else if (url.includes('/api/transactions')) {
      cacheKey = pwaStorage.TRANSACTIONS_CACHE;
    }
    
    if (cacheKey) {
      const cachedData = pwaStorage.get(cacheKey);
      if (cachedData) {
        console.log('Using cached data:', cacheKey);
        return { data: cachedData, success: true, offline: true };
      }
    }
    
    return { data: null, success: false, offline: true, error };
  }
}

/**
 * Check network connectivity
 */
function isOnline() {
  return navigator.onLine;
}

/**
 * Show offline indicator in UI
 */
function updateOnlineStatus() {
  const statusIndicator = document.getElementById('online-status') || createStatusIndicator();
  
  if (navigator.onLine) {
    statusIndicator.style.display = 'none';
  } else {
    statusIndicator.style.display = 'flex';
  }
}

/**
 * Create offline status indicator UI element
 */
function createStatusIndicator() {
  const indicator = document.createElement('div');
  indicator.id = 'online-status';
  indicator.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: #ef4444;
    color: white;
    padding: 12px;
    text-align: center;
    font-weight: 600;
    z-index: 10000;
    display: none;
  `;
  indicator.textContent = 'Offline Mode - Limited functionality';
  document.body.appendChild(indicator);
  return indicator;
}

/**
 * Listen to online/offline events
 */
window.addEventListener('online', () => {
  console.log('Back online!');
  updateOnlineStatus();
  // Refresh data when coming back online
  if (typeof loadPrice === 'function') loadPrice();
  if (typeof loadBalance === 'function') loadBalance();
});

window.addEventListener('offline', () => {
  console.log('Gone offline!');
  updateOnlineStatus();
});

/**
 * Initialize offline functionality
 */
function initializeOfflineSupport() {
  updateOnlineStatus();
  
  // Check for updates periodically
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    setInterval(() => {
      navigator.serviceWorker.controller.postMessage({ action: 'checkForUpdates' });
    }, 300000); // Every 5 minutes
  }
}

// Request background sync permission for price updates
function requestBackgroundSync() {
  if ('serviceWorker' in navigator && 'SyncManager' in window) {
    navigator.serviceWorker.ready.then(registration => {
      registration.sync.register('sync-price').catch(err => console.log('BG Sync failed:', err));
      registration.sync.register('sync-mints').catch(err => console.log('BG Sync failed:', err));
    });
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeOfflineSupport);
} else {
  initializeOfflineSupport();
}
