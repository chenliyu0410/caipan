// 菜盤 PWA Service Worker
const CACHE_NAME = 'caipan-shell-v2';
const DATA_CACHE_NAME = 'caipan-data-v1';

const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/favicon.svg',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png'
];

// 安裝時快取核心資源
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// 啟動時清理舊快取
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME && key !== DATA_CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 攔截請求：靜態資源快取優先，數據採用網路優先＋離線回退
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // 1. 行情數據請求：網路優先 (Network First)，失敗時回退快取
  if (url.pathname.includes('/data/latest.json')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response && response.status === 200) {
            const respClone = response.clone();
            caches.open(DATA_CACHE_NAME).then(cache => cache.put(event.request, respClone));
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }

  // 2. Google Fonts 資源快取
  if (url.origin.includes('fonts.googleapis.com') || url.origin.includes('fonts.gstatic.com')) {
    event.respondWith(
      caches.match(event.request).then(cached => {
        if (cached) return cached;
        return fetch(event.request).then(response => {
          const respClone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, respClone));
          return response;
        });
      })
    );
    return;
  }

  // 3. 一般靜態資源：快取優先 (Cache First)
  event.respondWith(
    caches.match(event.request).then(cached => {
      return cached || fetch(event.request).then(response => {
        // 如果是本站資源且成功，記錄快取
        if (response && response.status === 200 && event.request.method === 'GET') {
          const respClone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, respClone));
        }
        return response;
      });
    }).catch(() => {
      // 離線回退首頁
      if (event.request.mode === 'navigate') {
        return caches.match('./index.html');
      }
    })
  );
});
