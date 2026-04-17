const CACHE_NAME = 'e-wallet-v7';
const RUNTIME_CACHE = 'e-wallet-runtime-v7';
const DATA_CACHE = 'e-wallet-data-v7';

const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/static/css/style.css?v=7',
  '/static/js/app.js?v=6',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

const API_ENDPOINTS = [
  '/api/btc-price',
  '/api/btc-price-history',
  '/api/mints',
  '/api/wallet'
];

// Install - precache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
      .then(() => self.skipWaiting())
  );
});

// Activate - cleanup old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE && cacheName !== DATA_CACHE) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch - smart caching strategy
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // API endpoints - network first, fallback to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache successful API responses
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(DATA_CACHE).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Return cached data if offline
          return caches.match(request).then(cached => {
            if (cached) {
              return cached;
            }
            // Return offline response for missing data
            return new Response(JSON.stringify({
              offline: true,
              message: 'Using cached data. Connect to internet for updates.'
            }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
    return;
  }

  // Static assets - cache first, fallback to network
  if (request.headers.get('accept').includes('text/html') ||
      url.pathname.match(/\.(css|js|png|jpg|svg|woff|woff2)$/)) {
    event.respondWith(
      caches.match(request)
        .then(response => response || fetch(request))
        .then(response => {
          // Cache successful responses
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(RUNTIME_CACHE).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Default - network first
  event.respondWith(fetch(request).catch(() => caches.match('/index.html')));
});

// Handle background sync for offline data
self.addEventListener('sync', event => {
  if (event.tag === 'sync-price') {
    event.waitUntil(syncPriceData());
  }
  if (event.tag === 'sync-mints') {
    event.waitUntil(syncMintsData());
  }
});

async function syncPriceData() {
  try {
    const response = await fetch('/api/btc-price');
    if (response.ok) {
      const cache = await caches.open(DATA_CACHE);
      cache.put('/api/btc-price', response);
    }
  } catch (error) {
    console.log('Sync failed:', error);
  }
}

async function syncMintsData() {
  try {
    const response = await fetch('/api/mints');
    if (response.ok) {
      const cache = await caches.open(DATA_CACHE);
      cache.put('/api/mints', response);
    }
  } catch (error) {
    console.log('Sync failed:', error);
  }
}

// Message handler for cache control
self.addEventListener('message', event => {
  if (event.data.action === 'clearCache') {
    caches.keys().then(cacheNames => {
      Promise.all(cacheNames.map(cache => caches.delete(cache)));
    });
  }
  if (event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
});
