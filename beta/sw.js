/* Punto Ciego: caché para poder instalar la app y abrirla rápido. Red primero (siempre lo último publicado)
   y caché como respaldo sin conexión. Las partidas necesitan internet de todas formas.
   Al publicar una versión nueva, sube VERSION: el móvil descarga el sw.js nuevo, borra las cachés viejas
   y la página se recarga sola si está en la portada (ver el registro en index.html). */
/* Mudanza a puntostudio.es: cuando la dirección nueva ya responde, el SW limpia cachés, se desregistra y avisa a las páginas
   para que salten allí (un SW no puede navegar a otro origen, lo hace la página conservando query y hash). */
const NUEVA='https://puntostudio.es/punto-ciego/beta/';
const vivo=()=>!(location.hostname==='javivalmich.github.io')?Promise.resolve(false):fetch(NUEVA+'manifest.json',{cache:'no-store'}).then(r=>r.ok).catch(()=>false);
const ORIGEN_VIEJO=location.hostname==='javivalmich.github.io'; /* en puntostudio.es el destino siempre responde: la mudanza solo se hace desde la dirección antigua */
const mudar=()=>!ORIGEN_VIEJO?Promise.resolve():Promise.all([caches.keys().then(k=>Promise.all(k.map(x=>caches.delete(x)))),self.registration.unregister()]).then(()=>self.clients.matchAll({type:'window'})).then(cs=>cs.forEach(c=>c.postMessage('mudanza'))).catch(()=>{});
const VERSION='40';
const CACHE='punto-ciego-beta-v'+VERSION;
const SHELL=['./','index.html','manifest.json','privacidad.html','soporte.html','terminos.html','fonts/outfit-latin.woff2','assets/vendor/supabase-js/supabase.js','assets/logo-ciego.webp','assets/icons/favicon-32.png','assets/icons/icon-192.png','assets/icons/icon-512.png','assets/icons/apple-touch-icon.png'];
self.addEventListener('message',e=>{if(e.data==='skipWaiting')self.skipWaiting()});
self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>Promise.all(SHELL.map(u=>c.add(new Request(u,{cache:'reload'})).catch(()=>{})))).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()).then(vivo).then(ok=>{if(ok)return mudar()}));
});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const url=new URL(e.request.url);
  if(url.origin!==location.origin)return;
  e.respondWith(
    fetch(e.request,{cache:'no-cache'}).then(res=>{
      if(res.ok){const copy=res.clone();caches.open(CACHE).then(c=>c.put(e.request,copy))}
      if(res.type==='opaqueredirect')mudar(); /* GitHub ya redirige esta dirección al dominio nuevo */
      return res;
    }).catch(()=>caches.match(e.request,{ignoreSearch:true}).then(r=>r||caches.match('./')))
  );
});
