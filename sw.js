// Service Worker auto-limpante (desativa cache offline para garantir código 100% atualizado)
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(keys.map((key) => caches.delete(key)));
    })
  );
  self.clients.claim();
});

// Nunca intercepta; sempre busca da rede diretamente
self.addEventListener('fetch', (event) => {
  return;
});
