/* Αποθηκάριος: σερβίρει αρχεία από τη μνήμη του tablet όταν δεν υπάρχει ίντερνετ */
const SHELL = "shell-v3";   // άλλαξε v2, v3… όταν αλλάζεις index.html / sw.js
const FILES = ["./", "index.html", "manifest.json", "icon-192.png", "icon-512.png", "exhibits.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES.map(f => new Request(f, {cache: "reload"})))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(
    ks.filter(k => k.startsWith("shell-") && k !== SHELL).map(k => caches.delete(k))
  )).then(() => self.clients.claim()));
});

/* Το audio στο Android ζητά κομμάτια αρχείου (Range): τα εξυπηρετούμε από τη μνήμη */
async function rangeFrom(resp, req) {
  const m = /bytes=(\d*)-(\d*)/.exec(req.headers.get("range"));
  const buf = await resp.arrayBuffer();
  const start = m[1] ? parseInt(m[1]) : 0;
  const end = m[2] ? Math.min(parseInt(m[2]), buf.byteLength - 1) : buf.byteLength - 1;
  return new Response(buf.slice(start, end + 1), {
    status: 206,
    headers: {
      "Content-Type": resp.headers.get("Content-Type") || "audio/mpeg",
      "Content-Range": `bytes ${start}-${end}/${buf.byteLength}`,
      "Content-Length": end - start + 1
    }
  });
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin || new URL(req.url).searchParams.has("nc")) return;  // ?nc=... πάει κατευθείαν στο δίκτυο
  e.respondWith((async () => {
    const p = new URL(req.url).pathname;
    const isData = p.endsWith("exhibits.json") || p.endsWith("index.html") || p.endsWith("/");
    if (isData) {                       // σελίδα και λίστα: πρώτα δίκτυο (για ενημερώσεις), αλλιώς μνήμη
      try {
        const net = await fetch(req, {cache: "no-store"});
        const c = await caches.open(SHELL); c.put(req, net.clone());
        return net;
      } catch (_) { return (await caches.match(req)) || Response.error(); }
    }
    const hit = await caches.match(req, {ignoreSearch: true});
    if (hit) return req.headers.get("range") ? rangeFrom(hit, req) : hit;
    try { return await fetch(req); } catch (_) { return Response.error(); }
  })());
});
