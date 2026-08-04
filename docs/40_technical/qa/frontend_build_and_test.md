# Frontend build and test contract

Status: current
Date: 2026-08-03

The frontend now has a pinned Node 22 toolchain. Source modules live under
`frontend/src`, unit tests use Node's built-in test runner, and esbuild emits
browser bundles into `notas/static/notas/dist` for Django/WhiteNoise.

```bash
npm ci
npm test
npm run build
```

`package-lock.json` is the dependency authority. Generated bundles are committed
so local Django startup remains simple, while CI rebuilds them to catch source or
dependency failures. Render runs `npm ci --ignore-scripts` and builds before
`collectstatic`.

The first migrated module owns durable AI-job polling, transient mobile-network
backoff and idempotency-key creation. New interactive behavior should be added as
source modules with unit tests rather than as new inline template scripts.

CSS remains loaded as explicit component files. `home.css` and
`programs_charts.css` are the next decomposition targets; splitting them requires
visual regression evidence and must not be disguised as a mechanical rename.
