const assert = require('node:assert/strict');
const test = require('node:test');
const { currentPrices, compareNativePrices, normalizePrices } = require('./apple_price_preflight.cjs');

const now = Date.parse('2026-10-15T12:00:00Z');
const price = { territory: 'CHL', currency: 'CLP', customerPrice: '6990', startDate: null, endDate: null, preserved: false, planType: 'UPFRONT' };
const catalog = { appId: '6804048394', bundleId: 'com.myscoope.app', source: 'App Store Connect API',
  checkedAt: new Date(now).toISOString(), products: [{ id: 'com.myscoope.pro.monthly', name: 'Pro', prices: [price] }] };
const context = { id: '143483', countryCode: 'CHL', currency: 'CLP', observedAt: now - 1 };
const native = { loadedAt: now, before: context, after: context, result: 'accepted',
  requestedIds: ['com.myscoope.pro.monthly'], products: [{ id: 'com.myscoope.pro.monthly', currency: 'CLP', price: 6990, displayPrice: '$6.990' }] };
const copy = (value) => structuredClone(value);

test('Apple configuration alone cannot close app pricing', () => {
  assert.equal(currentPrices(catalog, 'CHL', now)[0].price, '6990');
  assert.throws(() => compareNativePrices(catalog, [], 'CHL', now), /Falta la captura nativa/);
});

test('fresh native quote matches the exact Apple SKU, currency and amount and preserves its display text', () => {
  const result = compareNativePrices(catalog, [native], 'CHL', now);
  assert.equal(result[0].displayPrice, '$6.990');
  const usd = copy(native);
  usd.products[0] = { ...usd.products[0], currency: 'USD', price: 5.99, displayPrice: '$5.99' };
  assert.throws(() => compareNativePrices(catalog, [usd], 'CHL', now), /Precio nativo distinto/);
  const wrongAmount = copy(native);
  wrongAmount.products[0].price = 5990;
  assert.throws(() => compareNativePrices(catalog, [wrongAmount], 'CHL', now), /Precio nativo distinto/);
});

test('last failed query, changed storefront and missing products cannot reuse an earlier success', () => {
  assert.throws(() => compareNativePrices(catalog, [native, { ...native, result: 'currency_mismatch' }], 'CHL', now), /no aceptada/);
  assert.throws(() => compareNativePrices(catalog, [{ ...native, after: { ...context, id: '143441' } }], 'CHL', now), /storefront/);
  assert.throws(() => compareNativePrices(catalog, [{ ...native, products: [] }], 'CHL', now), /exactamente/);
  assert.throws(() => compareNativePrices(catalog, [{ ...native, products: [native.products[0], native.products[0]] }], 'CHL', now), /exactamente/);
});

test('stale catalog, stale native quote, stale context and wrong app fail closed', () => {
  assert.throws(() => currentPrices({ ...catalog, checkedAt: '2026-10-13T00:00:00Z' }, 'CHL', now), /24 horas/);
  assert.throws(() => compareNativePrices(catalog, [{ ...native, loadedAt: now - 600_001 }], 'CHL', now), /10 minutos/);
  assert.throws(() => compareNativePrices(catalog, [{ ...native, before: { ...context, observedAt: now - 600_001 } }], 'CHL', now), /Contexto nativo obsoleto/);
  assert.throws(() => currentPrices({ ...catalog, appId: 'another-app' }, 'CHL', now), /no corresponde/);
});

test('current new-customer price excludes future and preserved prices and respects pack end dates', () => {
  const scheduled = copy(catalog);
  scheduled.products[0].prices.push({ ...price, customerPrice: '9990', startDate: '2026-11-01' },
    { ...price, customerPrice: '3990', preserved: true },
    { ...price, customerPrice: '4990', endDate: '2026-10-14' });
  assert.equal(currentPrices(scheduled, 'CHL', now)[0].price, '6990');
  scheduled.products[0].prices.push({ ...price, customerPrice: '7990', startDate: '2026-10-14' });
  assert.equal(currentPrices(scheduled, 'CHL', now)[0].price, '7990');
  scheduled.products[0].prices.push({ ...price, customerPrice: '8990', startDate: '2026-10-14' });
  assert.throws(() => currentPrices(scheduled, 'CHL', now), /ambiguos/);
});

test('decimal comparison supports other Apple currencies without a conversion or country table', () => {
  const french = copy(catalog);
  french.products[0].prices = [{ ...price, territory: 'FRA', currency: 'EUR', customerPrice: '6.9900' }];
  const front = { ...context, id: '143442', countryCode: 'FRA', currency: 'EUR' };
  const quote = { ...native, before: front, after: front,
    products: [{ ...native.products[0], currency: 'EUR', price: 6.99, displayPrice: '6,99 €' }] };
  assert.equal(compareNativePrices(french, [quote], 'FRA', now)[0].displayPrice, '6,99 €');
});

test('API relationship join uses customer price and territory currency', () => {
  const response = { data: [{ attributes: { startDate: null, preserved: false }, relationships: {
    territory: { data: { id: 'CHL' } }, subscriptionPricePoint: { data: { id: 'point' } },
  } }], included: [{ id: 'point', type: 'subscriptionPricePoints', attributes: { customerPrice: '6990', proceeds: '4993' } },
    { id: 'CHL', type: 'territories', attributes: { currency: 'CLP' } }] };
  assert.equal(normalizePrices(response, 'subscriptionPricePoint')[0].customerPrice, '6990');
  response.included.pop();
  assert.throws(() => normalizePrices(response, 'subscriptionPricePoint'), /incompleta/);
});
