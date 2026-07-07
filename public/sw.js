const SW_VERSION = 'zucai-pwa-v3';
const SHELL_CACHE = `${SW_VERSION}-shell`;
const RUNTIME_CACHE = `${SW_VERSION}-runtime`;
const SHELL = [
  './',
  './index.html',
  './table.html',
  './table-zfc.html',
  './formula.html',
  './three.module.min.js',
  './manifest.webmanifest',
  './icon.svg',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL)).catch(() => undefined));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => !k.startsWith(SW_VERSION)).map(k => caches.delete(k)))));
  self.clients.claim();
});

function fetchWithTimeout(request, ms){
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), ms);
  return fetch(request, {signal: ctl.signal}).finally(() => clearTimeout(timer));
}

self.addEventListener('fetch', event => {
  const req = event.request;
  if(req.method !== 'GET') return;
  const url = new URL(req.url);
  if(url.origin !== location.origin) return;
  if(url.pathname.includes('/api/')){
    event.respondWith(fetchWithTimeout(req, 5000).then(res => {
      const copy = res.clone();
      caches.open(RUNTIME_CACHE).then(cache => cache.put(req, copy));
      return res;
    }).catch(() => caches.match(req).then(hit => hit || Response.error())));
    return;
  }
  // HTML 文档 network-first：部署即生效，离线回退缓存（否则 cache-first 会让用户一直拿旧版应用）
  if(req.mode === 'navigate' || req.destination === 'document' || url.pathname.endsWith('.html') || url.pathname === '/'){
    event.respondWith(fetchWithTimeout(req, 4000).then(res => {
      const copy = res.clone();
      caches.open(RUNTIME_CACHE).then(cache => cache.put(req, copy));
      return res;
    }).catch(() => caches.match(req, {ignoreSearch: true}).then(hit => hit || caches.match('./index.html'))));
    return;
  }
  // 其余静态资源 cache-first
  event.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
    const copy = res.clone();
    caches.open(RUNTIME_CACHE).then(cache => cache.put(req, copy));
    return res;
  })));
});
