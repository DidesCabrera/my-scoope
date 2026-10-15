#!/usr/bin/env node
// Development/release evidence only. Never imported by the app or used to set prices.
const { readFileSync, writeFileSync } = require('node:fs');
const { createRequire } = require('node:module');
const { resolve } = require('node:path');
const { parseArgs } = require('node:util');

const APP_ID = '6804048394';
const PROJECT_ID = 'ea9b4286-222a-4b79-93da-584ed07ed072';
const BUNDLE_ID = 'com.myscoope.app';

function decimal(value) {
  const text = String(value);
  if (!/^\d+(?:\.\d+)?$/.test(text)) throw new Error('Precio decimal inválido');
  const [whole, fraction = ''] = text.split('.');
  return `${whole.replace(/^0+(?=\d)/, '')}${fraction.replace(/0+$/, '') ? `.${fraction.replace(/0+$/, '')}` : ''}`;
}

function currentPrices(catalog, territory, now = Date.now()) {
  if (catalog.appId !== APP_ID || catalog.bundleId !== BUNDLE_ID || catalog.source !== 'App Store Connect API') {
    throw new Error('El catálogo no corresponde a My Scoope en Apple');
  }
  const checkedAt = Date.parse(catalog.checkedAt);
  if (!Number.isFinite(checkedAt) || now - checkedAt > 24 * 3600_000 || checkedAt > now + 60_000) {
    throw new Error('Vuelve a consultar Apple: el catálogo debe tener menos de 24 horas');
  }
  if (!catalog.products?.length) throw new Error('Catálogo vacío');
  const seen = new Set();
  return catalog.products.map((product) => {
    if (!product.id || seen.has(product.id)) throw new Error('ID de producto ausente o duplicado');
    seen.add(product.id);
    const eligible = product.prices.filter((price) => price.territory === territory && !price.preserved
      && (!price.planType || price.planType === 'UPFRONT')
      && (!price.startDate || Date.parse(price.startDate) <= now)
      && (!price.endDate || Date.parse(price.endDate) > now));
    eligible.sort((a, b) => (Date.parse(b.startDate) || 0) - (Date.parse(a.startDate) || 0));
    const price = eligible[0];
    if (!price?.currency || !price.customerPrice) throw new Error(`Sin precio vigente: ${product.id}/${territory}`);
    if (eligible[1] && eligible[1].startDate === price.startDate) throw new Error(`Precios ambiguos: ${product.id}/${territory}`);
    return { id: product.id, name: product.name, territory, currency: price.currency, price: decimal(price.customerPrice) };
  });
}

function compareNativePrices(catalog, diagnostics, territory, now = Date.now()) {
  const expected = currentPrices(catalog, territory, now);
  const sample = Array.isArray(diagnostics) ? diagnostics.at(-1) : null;
  if (!sample) throw new Error('Falta la captura nativa; consultar Apple no cierra la validación de la app');
  if (sample.result !== 'accepted') throw new Error(`Última consulta nativa no aceptada: ${sample.result}`);
  if (!Number.isFinite(sample.loadedAt) || now - sample.loadedAt > 10 * 60_000 || sample.loadedAt > now + 60_000) {
    throw new Error('La captura nativa debe tener menos de 10 minutos');
  }
  const { before, after } = sample;
  if (!before?.id || !after?.currency || before.id !== after.id || before.countryCode !== after.countryCode
    || before.currency !== after.currency || after.countryCode !== territory) {
    throw new Error('El storefront cambió, es desconocido o no corresponde al país solicitado');
  }
  for (const context of [before, after]) {
    if (!Number.isFinite(context.observedAt) || context.observedAt > sample.loadedAt + 1000
      || sample.loadedAt - context.observedAt > 10 * 60_000) throw new Error('Contexto nativo obsoleto');
  }
  const ids = expected.map((item) => item.id).sort();
  if (JSON.stringify([...sample.requestedIds].sort()) !== JSON.stringify(ids)
    || JSON.stringify(sample.products.map((item) => item.id).sort()) !== JSON.stringify(ids)) {
    throw new Error('Los IDs solicitados y recibidos deben cubrir exactamente el catálogo de Apple');
  }
  return expected.map((price) => {
    const native = sample.products.find((item) => item.id === price.id);
    if (native.currency !== price.currency || after.currency !== price.currency || native.price == null
      || decimal(native.price) !== price.price || !native.displayPrice?.trim()) {
      throw new Error(`Precio nativo distinto de Apple: ${price.id} (${native.currency ?? '?'} ${native.price ?? '?'}, esperado ${price.currency} ${price.price})`);
    }
    return { ...price, displayPrice: native.displayPrice };
  });
}

function normalizePrices(response, relation) {
  return response.data.map((item) => {
    const territory = item.relationships.territory.data.id;
    const pointId = item.relationships[relation].data.id;
    const point = response.included.find((row) => row.id === pointId && row.type.endsWith('PricePoints'));
    const region = response.included.find((row) => row.type === 'territories' && row.id === territory);
    if (!point || !region) throw new Error('Respuesta de precios incompleta de Apple');
    return { territory, currency: region.attributes.currency, customerPrice: point.attributes.customerPrice,
      startDate: item.attributes.startDate ?? null, endDate: item.attributes.endDate ?? null,
      preserved: item.attributes.preserved ?? false, planType: item.attributes.planType ?? null };
  });
}

async function readAppleCatalog({ cliRoot, projectDir, territories, out }) {
  // Reuse the official CLI's existing authenticated project context. Keys/tokens
  // stay inside the process; only product and customer-price fields are written.
  const cliRequire = createRequire(resolve(cliRoot, 'package.json'));
  const { Config } = cliRequire('@oclif/core');
  const BaseStatus = cliRequire('./build/commands/submit/status').default;
  const { resolveTestFlightAppAsync } = cliRequire('./build/testflight/app');
  process.chdir(projectDir);
  class PriceReader extends BaseStatus {
    async runAsync() {
      const context = await this.getContextAsync(PriceReader, { nonInteractive: true, withServerSideEnvironment: null });
      const { actor, graphqlClient } = context.loggedIn;
      const { exp, projectId, projectDir: directory } = context.privateProjectConfig;
      if (projectId !== PROJECT_ID) throw new Error('Proyecto EAS inesperado');
      const app = await resolveTestFlightAppAsync({ actor, graphqlClient, exp, projectId, projectDir: directory,
        analytics: context.analytics, vcsClient: context.vcsClient, nonInteractive: true, profileName: 'testflight-production' });
      if (app.id !== APP_ID || app.attributes.bundleId !== BUNDLE_ID) throw new Error('App Apple inesperada');
      const auth = app.context.token;
      if (!auth) throw new Error('Falta el acceso existente a la API de Apple');
      const get = async (path) => {
        const result = { data: [], included: [] };
        const visited = new Set();
        let next = path;
        while (next) {
          const url = new URL(next, 'https://api.appstoreconnect.apple.com');
          if (url.origin !== 'https://api.appstoreconnect.apple.com' || visited.has(url.href) || visited.size >= 100) {
            throw new Error('Paginación inesperada de Apple');
          }
          visited.add(url.href);
          const token = typeof auth === 'string' ? auth : await auth.getToken();
          const response = await fetch(url, { method: 'GET', redirect: 'error',
            headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' }, signal: AbortSignal.timeout(30_000) });
          if (!response.ok) throw new Error(`Apple respondió ${response.status} en ${url.pathname}`);
          const body = await response.json();
          result.data.push(...(Array.isArray(body.data) ? body.data : [body.data]));
          result.included.push(...(body.included ?? []));
          next = body.links?.next;
        }
        return result;
      };
      const query = (relation) => new URLSearchParams({ 'filter[territory]': territories.join(','),
        include: `${relation},territory`, limit: '200' }).toString();
      const groups = await get(`/v1/apps/${APP_ID}/subscriptionGroups?limit=200`);
      const subscriptions = (await Promise.all(groups.data.map((group) => get(`/v1/subscriptionGroups/${group.id}/subscriptions?limit=100`)))).flatMap((page) => page.data);
      const packs = (await get(`/v1/apps/${APP_ID}/inAppPurchasesV2?limit=200`)).data.filter((item) => item.attributes.inAppPurchaseType === 'CONSUMABLE');
      const products = await Promise.all([
        ...subscriptions.map(async (item) => ({ id: item.attributes.productId, appleId: item.id, name: item.attributes.name,
          kind: 'subscription', period: item.attributes.subscriptionPeriod,
          prices: normalizePrices(await get(`/v1/subscriptions/${item.id}/prices?${query('subscriptionPricePoint')}`), 'subscriptionPricePoint') })),
        ...packs.map(async (item) => {
          const schedule = (await get(`/v2/inAppPurchases/${item.id}/iapPriceSchedule`)).data[0];
          const [manual, automatic] = await Promise.all(['manualPrices', 'automaticPrices'].map((type) =>
            get(`/v1/inAppPurchasePriceSchedules/${schedule.id}/${type}?${query('inAppPurchasePricePoint')}`)));
          return { id: item.attributes.productId, appleId: item.id, name: item.attributes.name, kind: 'credit_pack',
            prices: [...normalizePrices(manual, 'inAppPurchasePricePoint'), ...normalizePrices(automatic, 'inAppPurchasePricePoint')] };
        }),
      ]);
      const catalog = { appId: APP_ID, bundleId: BUNDLE_ID, source: 'App Store Connect API',
        checkedAt: new Date().toISOString(), territories, products };
      for (const territory of territories) currentPrices(catalog, territory);
      writeFileSync(out, `${JSON.stringify(catalog, null, 2)}\n`);
      console.log(`Catálogo de Apple consultado: ${products.length} productos, ${territories.join(', ')}. Archivo: ${out}`);
      console.log('Sólo configuración comprobada. Falta comparar la captura nativa de la app.');
    }
  }
  await PriceReader.run([], await Config.load(cliRoot));
}

async function main() {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: {
    'eas-cli-root': { type: 'string' }, 'project-dir': { type: 'string' }, out: { type: 'string' },
    catalog: { type: 'string' }, diagnostics: { type: 'string' }, territory: { type: 'string', default: 'CHL' },
    territories: { type: 'string', default: 'CHL,USA,FRA,JPN' },
  } });
  if (positionals[0] === 'read') {
    if (!values['eas-cli-root'] || !values.out) throw new Error('read exige --eas-cli-root y --out');
    return readAppleCatalog({ cliRoot: resolve(values['eas-cli-root']), projectDir: resolve(values['project-dir'] ?? 'mobile'),
      territories: values.territories.split(',').map((item) => item.trim()), out: resolve(values.out) });
  }
  if (positionals[0] !== 'check' || !values.catalog) throw new Error('Uso: read --eas-cli-root RUTA --out ARCHIVO | check --catalog ARCHIVO --diagnostics CAPTURA --territory CHL');
  const catalog = JSON.parse(readFileSync(values.catalog, 'utf8'));
  if (!values.diagnostics) {
    console.table(currentPrices(catalog, values.territory));
    throw new Error('Catálogo comprobado; falta --diagnostics. El precio de la app sigue abierto');
  }
  const comparison = compareNativePrices(catalog, JSON.parse(readFileSync(values.diagnostics, 'utf8')), values.territory);
  console.table(comparison);
  console.log('La captura nativa coincide con el catálogo vigente de Apple. Verifica en el cliente de desarrollo que la pantalla conserva estos textos. Esta comparación no certifica el entorno TestFlight.');
}

module.exports = { currentPrices, compareNativePrices, normalizePrices };
if (require.main === module) main().catch((error) => {
  // Do not stringify CLI/HTTP errors; they may contain authentication context.
  console.error(`Precio sin cerrar: ${error instanceof Error ? error.message : 'consulta fallida'}`);
  process.exitCode = 1;
});
