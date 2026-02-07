const CACHE_NAME = 'courtside-v1';
const ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    '/static/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(ASSETS))
    );
});

self.addEventListener('fetch', (event) => {
    // API: Network Only
    if (event.request.url.includes('/predict') || event.request.url.includes('/history')) {
        return;
    }

    // Static: Cache First
    event.respondWith(
        caches.match(event.request)
            .then((response) => response || fetch(event.request))
    );
});
