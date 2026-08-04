import base64

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET

from notas.interface.views.pwa_startup_images import (
    PWA_STARTUP_IMAGE_SPECS,
    pwa_startup_image_bytes,
)

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
    shortcut_calendarization_url = reverse("calendarization_dashboard")

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
                "name": "Calendarizar programa",
                "short_name": "Calendarizar",
                "url": shortcut_calendarization_url,
                "icons": [{"src": icon_192_url, "sizes": "192x192", "type": "image/png"}],
            },
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
def pwa_startup_image(request, image_key):
    """Return a generated iOS/iPadOS startup image for the PWA splash screen."""
    startup_image = pwa_startup_image_bytes(image_key)

    if startup_image is None:
        raise Http404("PWA startup image not available")

    response = HttpResponse(startup_image, content_type="image/png")
    response["Cache-Control"] = "public, max-age=604800"
    return response


def pwa_startup_image_specs():
    """Expose the supported startup image metadata for templates and documentation."""
    return PWA_STARTUP_IMAGE_SPECS


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

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = { title: "MyScoope", body: event.data ? event.data.text() : "" };
  }

  const title = payload.title || "MyScoope";
  const options = {
    body: payload.body || "Tu plan está listo.",
    data: { url: payload.url || "/app/calendarization/" },
    tag: payload.tag || "myscoope-calendarization",
    renotify: false,
    icon: "/app/icons/192.png",
    badge: "/app/icons/192.png",
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = new URL(
    (event.notification.data && event.notification.data.url) || "/app/calendarization/",
    self.location.origin
  ).href;

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      const existing = windows.find((client) => client.url === targetUrl);
      return existing ? existing.focus() : clients.openWindow(targetUrl);
    })
  );
});
""".strip().replace("__CACHE_VERSION__", str(cache_version))

    response = HttpResponse(content, content_type="text/javascript")
    response["Service-Worker-Allowed"] = "/app/"
    response["Cache-Control"] = "no-cache"
    return response
