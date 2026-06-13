import base64

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET


PWA_ICON_PNG_BASE64 = {
    180: """
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
""",
    192: """
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
""",
    512: """
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
""",
}


@require_GET
def pwa_manifest(request):
    """Return the installable app manifest for the authenticated app shell."""
    start_url = reverse("home_view")
    icon_192_url = reverse("pwa_icon", kwargs={"size": 192})
    icon_512_url = reverse("pwa_icon", kwargs={"size": 512})
    shortcut_dailyplans_url = reverse("dailyplan_list")
    shortcut_meals_url = reverse("meal_list")
    shortcut_foods_url = reverse("food_list")

    manifest = {
        "name": "MyScoope",
        "short_name": "MyScoope",
        "description": "Planificación nutricional deportiva con comidas, planes diarios y propuestas IA.",
        "id": start_url,
        "start_url": start_url,
        "scope": "/app/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "orientation": "portrait-primary",
        "background_color": "#000000",
        "theme_color": "#000000",
        "categories": ["health", "fitness", "productivity"],
        "icons": [
            {
                "src": icon_192_url,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": icon_512_url,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
        "shortcuts": [
            {
                "name": "Mis Planes Diarios",
                "short_name": "Planes",
                "url": shortcut_dailyplans_url,
                "icons": [{"src": icon_192_url, "sizes": "192x192", "type": "image/png"}],
            },
            {
                "name": "Mis Comidas",
                "short_name": "Comidas",
                "url": shortcut_meals_url,
                "icons": [{"src": icon_192_url, "sizes": "192x192", "type": "image/png"}],
            },
            {
                "name": "Mis Alimentos",
                "short_name": "Alimentos",
                "url": shortcut_foods_url,
                "icons": [{"src": icon_192_url, "sizes": "192x192", "type": "image/png"}],
            },
        ],
    }

    response = JsonResponse(manifest)
    response["Content-Type"] = "application/manifest+json"
    return response


@require_GET
def pwa_icon(request, size):
    """Return generated PNG icons without adding binary files to the repository."""
    icon_base64 = PWA_ICON_PNG_BASE64.get(size)

    if not icon_base64:
        raise Http404("PWA icon size not available")

    response = HttpResponse(base64.b64decode(icon_base64), content_type="image/png")
    response["Cache-Control"] = "public, max-age=86400"
    return response


@require_GET
def pwa_service_worker(request):
    """Serve a conservative service worker scoped to /app/."""
    cache_version = getattr(settings, "MYSCOOPE_PWA_CACHE_VERSION", "v1")
    content = """
const CACHE_NAME = "myscoope-static-__CACHE_VERSION__";
const STATIC_PATH_PREFIX = "/static/";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => (
      Promise.all(
        keys
          .filter((key) => key.startsWith("myscoope-static-") && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;

  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  if (url.origin !== self.location.origin || !url.pathname.startsWith(STATIC_PATH_PREFIX)) {
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then((cache) => (
      cache.match(request).then((cachedResponse) => {
        const networkFetch = fetch(request)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.ok) {
              cache.put(request, networkResponse.clone());
            }
            return networkResponse;
          })
          .catch(() => cachedResponse);

        return cachedResponse || networkFetch;
      })
    ))
  );
});
""".strip().replace("__CACHE_VERSION__", str(cache_version))

    response = HttpResponse(content, content_type="text/javascript")
    response["Service-Worker-Allowed"] = "/app/"
    response["Cache-Control"] = "no-cache"
    return response
