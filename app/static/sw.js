// ============================================================
// FACEATTEND SERVICE WORKER — PWA Offline & Cache Manager
// Version: 1.0.0
// Scope: / (root, so it controls every page)
// ============================================================

const CACHE_NAME = 'faceattend-v1';

// Assets to cache on install — app shell (loads instantly even offline)
const STATIC_ASSETS = [
    '/',
    '/dashboard',
    '/camera',
    '/report',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/img/logo.png',
    '/static/manifest.json',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css',
];

// ── INSTALL: Cache all static shell assets ──
self.addEventListener('install', event => {
    console.log('[SW] Installing FaceAttend Service Worker...');
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return Promise.allSettled(
                STATIC_ASSETS.map(url =>
                    cache.add(url).catch(err => {
                        console.warn(`[SW] Could not cache ${url}:`, err);
                    })
                )
            );
        }).then(() => {
            console.log('[SW] Installation complete.');
            return self.skipWaiting(); // activate immediately
        })
    );
});

// ── ACTIVATE: Clean up old caches ──
self.addEventListener('activate', event => {
    console.log('[SW] Activating FaceAttend Service Worker...');
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(key => key !== CACHE_NAME)
                    .map(key => {
                        console.log('[SW] Deleting old cache:', key);
                        return caches.delete(key);
                    })
            )
        ).then(() => self.clients.claim()) // take control of all open tabs
    );
});

// ── FETCH: Network-first for API/auth, Cache-first for static assets ──
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // ❌ Never intercept: API calls, auth, admin actions, camera streams
    const bypassPaths = [
        '/api/',
        '/auth/',
        '/admin/',
        '/static/uploads/',
    ];
    const shouldBypass = bypassPaths.some(p => url.pathname.startsWith(p));

    if (
        event.request.method !== 'GET' ||
        shouldBypass ||
        url.origin !== location.origin && !url.hostname.includes('jsdelivr.net')
    ) {
        // Pass through to network directly — no caching
        return;
    }

    // ✅ Strategy: Network-first (fresh data), fallback to cache
    event.respondWith(
        fetch(event.request)
            .then(networkResponse => {
                // Cache successful responses for future offline use
                if (networkResponse && networkResponse.status === 200) {
                    const responseToCache = networkResponse.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseToCache);
                    });
                }
                return networkResponse;
            })
            .catch(() => {
                // Network failed → serve from cache
                return caches.match(event.request).then(cachedResponse => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    // If page not cached, return offline notice
                    if (event.request.headers.get('accept').includes('text/html')) {
                        return new Response(
                            `<!DOCTYPE html>
                            <html lang="en">
                            <head>
                                <meta charset="UTF-8">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>FaceAttend — Offline</title>
                                <style>
                                    body { font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f8fafc; }
                                    .box { text-align: center; padding: 2rem; max-width: 360px; }
                                    .icon { font-size: 4rem; margin-bottom: 1rem; }
                                    h2 { color: #1e293b; margin-bottom: 0.5rem; }
                                    p { color: #64748b; margin-bottom: 1.5rem; }
                                    button { background: #2563eb; color: white; border: none; padding: 0.75rem 2rem; border-radius: 8px; font-size: 1rem; cursor: pointer; }
                                    button:hover { background: #1d4ed8; }
                                </style>
                            </head>
                            <body>
                                <div class="box">
                                    <div class="icon">📡</div>
                                    <h2>You're Offline</h2>
                                    <p>FaceAttend needs an internet connection to scan and verify your face. Please reconnect and try again.</p>
                                    <button onclick="location.reload()">🔄 Try Again</button>
                                </div>
                            </body>
                            </html>`,
                            { headers: { 'Content-Type': 'text/html' } }
                        );
                    }
                });
            })
    );
});

// ── BACKGROUND SYNC: Retry failed attendance marks ──
self.addEventListener('sync', event => {
    if (event.tag === 'sync-attendance') {
        console.log('[SW] Background sync: retrying attendance...');
    }
});
