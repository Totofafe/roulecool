// RouleCool — Service Worker
// ⚠️ INCRÉMENTER LA VERSION À CHAQUE GIT PUSH (v1 → v2 → v3...)
// Cela force le rechargement du cache sur les appareils des utilisateurs.

const CACHE_NAME = 'roulecool-v25';

// Fichiers à mettre en cache au premier chargement
const CACHE_FILES = [
  '/roulecool/',
  '/roulecool/index.html',
  '/roulecool/enregistrement.html',
  '/roulecool/seuils.js',
  '/roulecool/manifest.json',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@400;500&display=swap',
];

// Installation : mise en cache des ressources essentielles
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[SW] Mise en cache des ressources');
      // On ignore les erreurs individuelles pour ne pas bloquer l'install
      return Promise.allSettled(
        CACHE_FILES.map(url => cache.add(url).catch(() => {}))
      );
    })
  );
  self.skipWaiting();
});

// Activation : nettoyage des anciens caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Interception des requêtes : cache-first pour les assets, network-first pour l'API
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Ne pas intercepter les appels vers Grist/Cloudflare
  if (url.hostname.includes('workers.dev') || url.hostname.includes('grist')) {
    return;
  }

  // Ne pas intercepter les appels Panoramax
  if (url.hostname.includes('panoramax')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        // Mettre en cache les nouvelles ressources statiques
        if (response.ok && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // Hors ligne : retourner la page principale si possible
        if (event.request.destination === 'document') {
          return caches.match('/roulecool/index.html');
        }
      });
    })
  );
});
