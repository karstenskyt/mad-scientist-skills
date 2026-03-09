# Frontend Performance & API Optimization Reference

Comprehensive guide to Core Web Vitals, bundle optimization, image optimization, rendering performance, font loading, third-party script management, API response optimization, and performance budgets.

## Purpose

Answer: "Is the frontend fast, resource-efficient, and providing a good user experience — and are APIs shaped and sized for efficient delivery?"

## Checklist

Before auditing, identify:

- [ ] Which frontend framework is in use (React, Vue, Svelte, Angular, vanilla)
- [ ] Which bundler is configured (webpack, Vite, Rollup, esbuild, Turbopack)
- [ ] Whether a CDN is in front of static assets
- [ ] Whether Core Web Vitals are currently measured (CrUX, Lighthouse CI, RUM)
- [ ] Whether performance budgets are defined and enforced
- [ ] Which API patterns are in use (REST, GraphQL, gRPC, tRPC)

---

## Core Web Vitals

Core Web Vitals are Google's user-centric performance metrics. They measure loading, interactivity, and visual stability.

| Metric | Good | Needs Improvement | Poor | What it measures |
|--------|------|-------------------|------|-----------------|
| **LCP** (Largest Contentful Paint) | < 2.5s | 2.5s - 4.0s | > 4.0s | Loading performance — when the largest element is visible |
| **INP** (Interaction to Next Paint) | < 200ms | 200ms - 500ms | > 500ms | Responsiveness — delay between user input and visual update |
| **CLS** (Cumulative Layout Shift) | < 0.1 | 0.1 - 0.25 | > 0.25 | Visual stability — how much the layout shifts unexpectedly |

### Supporting metrics

| Metric | Target | What it measures |
|--------|--------|-----------------|
| FCP (First Contentful Paint) | < 1.8s | Perceived load speed — when first content appears |
| TTFB (Time to First Byte) | < 800ms | Server responsiveness — time until first byte arrives |
| Total Bundle Size (JS) | < 200KB gzipped (initial) | Transfer efficiency |
| Total Transfer Size | < 1MB (initial page load) | Overall page weight |

### LCP optimization

The Largest Contentful Paint element is typically a hero image, video poster, or large text block. Optimize the critical path to that element.

**Common LCP elements and fixes:**

| LCP element | Optimization |
|-------------|-------------|
| Hero image | Preload with `<link rel="preload">`, use `fetchpriority="high"`, serve WebP/AVIF |
| Background image (CSS) | Inline critical CSS, preload the image, avoid `background-image` for LCP |
| Large text block | Inline critical font CSS, use `font-display: swap`, preload font file |
| Video poster | Preload poster image, avoid auto-play blocking render |

```html
<!-- GOOD: Preload LCP image with high priority -->
<head>
  <link rel="preload" as="image" href="/hero.webp" fetchpriority="high">
</head>
<body>
  <img src="/hero.webp" alt="Hero" fetchpriority="high" width="1200" height="600">
</body>
```

```html
<!-- BAD: LCP image loads late, no preload, no dimensions -->
<body>
  <img src="/hero.png" alt="Hero">
</body>
```

### INP optimization

INP measures the worst interaction responsiveness. Reduce main thread blocking to keep interactions fast.

**Strategies:**

- Break long tasks (>50ms) into smaller chunks using `scheduler.yield()` or `setTimeout`
- Move heavy computation to Web Workers
- Debounce rapid input handlers (search, scroll)
- Use `content-visibility: auto` for off-screen rendering
- Avoid synchronous layout reads in event handlers

```javascript
// GOOD: Break long task to yield to the main thread
async function processLargeList(items) {
  const CHUNK_SIZE = 100;
  for (let i = 0; i < items.length; i += CHUNK_SIZE) {
    const chunk = items.slice(i, i + CHUNK_SIZE);
    processChunk(chunk);

    // Yield to the main thread between chunks
    if (i + CHUNK_SIZE < items.length) {
      await scheduler.yield();
    }
  }
}
```

```javascript
// BAD: Long task blocks the main thread for the entire duration
function processLargeList(items) {
  items.forEach(item => {
    // 10,000 items processed synchronously — blocks all interactions
    expensiveOperation(item);
  });
}
```

### CLS optimization

CLS is caused by elements shifting after initial render. Reserve space for dynamic content.

**Common CLS causes and fixes:**

| Cause | Fix |
|-------|-----|
| Images without dimensions | Always set `width` and `height` attributes |
| Ads / embeds without reserved space | Use `aspect-ratio` or explicit container sizing |
| Dynamically injected content | Reserve space with `min-height` or skeleton placeholders |
| Web fonts causing text reflow | Use `font-display: swap` with size-adjusted fallback |
| Late-loading above-the-fold content | Server-render or preload critical content |

```html
<!-- GOOD: Image with explicit dimensions prevents layout shift -->
<img src="/product.webp" alt="Product" width="400" height="300" loading="lazy">
```

```html
<!-- BAD: No dimensions — layout shifts when image loads -->
<img src="/product.webp" alt="Product" loading="lazy">
```

```css
/* GOOD: Reserve space for dynamic content with aspect-ratio */
.video-embed {
  aspect-ratio: 16 / 9;
  width: 100%;
}
```

---

## Bundle Optimization

### Route-based code splitting

Split the bundle by route so users only download code for the page they visit.

```javascript
// GOOD: React — route-based splitting with React.lazy
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
const Analytics = lazy(() => import('./pages/Analytics'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/analytics" element={<Analytics />} />
      </Routes>
    </Suspense>
  );
}
```

```javascript
// BAD: All routes imported statically — entire app in one bundle
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Analytics from './pages/Analytics';
```

```javascript
// GOOD: Next.js — dynamic import with loading state
import dynamic from 'next/dynamic';

const HeavyChart = dynamic(() => import('../components/HeavyChart'), {
  loading: () => <ChartSkeleton />,
  ssr: false,
});
```

```javascript
// GOOD: Vue — async component for route splitting
const routes = [
  {
    path: '/dashboard',
    component: () => import('./views/Dashboard.vue'),
  },
  {
    path: '/analytics',
    component: () => import('./views/Analytics.vue'),
  },
];
```

### Component-level splitting

Split heavy components that are not needed on initial render.

```javascript
// GOOD: Dynamic import for heavy library used in one component
async function renderChart(data) {
  const { Chart } = await import('chart.js');
  const chart = new Chart(canvas, { data });
}
```

```javascript
// BAD: Static import of heavy library — included in initial bundle
import { Chart } from 'chart.js'; // ~200KB
```

### Tree-shaking configuration

Tree-shaking eliminates dead code from production bundles. It requires ES module syntax (`import`/`export`) and proper configuration.

```json
// GOOD: package.json — mark package as side-effect-free for tree-shaking
{
  "name": "my-library",
  "sideEffects": false
}
```

```json
// GOOD: package.json — only specific files have side effects
{
  "sideEffects": ["*.css", "./src/polyfills.js"]
}
```

```javascript
// GOOD: Named imports — tree-shakeable
import { debounce } from 'lodash-es';
```

```javascript
// BAD: Default import of entire library — not tree-shakeable
import _ from 'lodash';
```

### Per-bundler code splitting configuration

**webpack:**

```javascript
// webpack.config.js
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      maxInitialRequests: 20,
      minSize: 20000,
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name(module) {
            const match = module.context.match(
              /[\\/]node_modules[\\/](.*?)([\\/]|$)/
            );
            return match ? `vendor.${match[1].replace('@', '')}` : 'vendor';
          },
        },
        common: {
          minChunks: 2,
          priority: -10,
          reuseExistingChunk: true,
        },
      },
    },
  },
};
```

**Vite:**

```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'chart-vendor': ['chart.js', 'd3'],
          'ui-vendor': ['@radix-ui/react-dialog', '@radix-ui/react-popover'],
        },
      },
    },
  },
});
```

**Rollup:**

```javascript
// rollup.config.js
export default {
  input: {
    main: 'src/main.js',
    dashboard: 'src/dashboard.js',
  },
  output: {
    dir: 'dist',
    format: 'es',
    chunkFileNames: 'chunks/[name]-[hash].js',
  },
};
```

---

## Image Optimization

### Format selection

| Format | Best for | Browser support | Compression |
|--------|----------|----------------|-------------|
| **WebP** | Photos, illustrations | All modern browsers | 25-35% smaller than JPEG |
| **AVIF** | Photos (best compression) | Chrome, Firefox, Safari 16.4+ | 50% smaller than JPEG |
| **SVG** | Icons, logos, simple graphics | All browsers | Infinitely scalable |
| **PNG** | Screenshots, transparency needed | All browsers | Lossless, large files |
| **JPEG** | Legacy fallback for photos | All browsers | Good compression, no transparency |

### Responsive images

```html
<!-- GOOD: <picture> element with modern format fallback chain -->
<picture>
  <source srcset="/hero.avif" type="image/avif">
  <source srcset="/hero.webp" type="image/webp">
  <img src="/hero.jpg" alt="Hero image" width="1200" height="600"
       loading="lazy" decoding="async">
</picture>
```

```html
<!-- GOOD: srcset for resolution switching -->
<img
  srcset="/product-400w.webp 400w,
          /product-800w.webp 800w,
          /product-1200w.webp 1200w"
  sizes="(max-width: 600px) 400px,
         (max-width: 1000px) 800px,
         1200px"
  src="/product-800w.webp"
  alt="Product"
  width="800"
  height="600"
  loading="lazy"
  decoding="async"
>
```

### Lazy loading

```html
<!-- GOOD: Native lazy loading for below-fold images -->
<img src="/photo.webp" alt="Photo" loading="lazy" decoding="async"
     width="400" height="300">

<!-- GOOD: Eager loading for above-fold LCP image -->
<img src="/hero.webp" alt="Hero" loading="eager" fetchpriority="high"
     width="1200" height="600">
```

```html
<!-- BAD: All images load eagerly — wastes bandwidth -->
<img src="/photo1.webp" alt="Photo 1">
<img src="/photo2.webp" alt="Photo 2">
<img src="/photo3.webp" alt="Photo 3">
```

### Image compression tools

| Tool | Type | Usage |
|------|------|-------|
| `sharp` (Node.js) | Build-time | `sharp(input).webp({ quality: 80 }).toFile(output)` |
| `squoosh` | CLI / Web UI | `squoosh-cli --webp '{"quality":80}' image.png` |
| `imagemin` | Build pipeline | webpack/Vite plugin for automatic optimization |
| Cloudinary / imgix | CDN | URL-based transforms: `?w=800&f=webp&q=80` |
| Vercel Image Optimization | CDN | `next/image` with automatic format/size optimization |

### CDN image optimization

```html
<!-- GOOD: CDN-based image optimization with URL parameters -->
<img
  src="https://cdn.example.com/images/product.jpg?w=800&h=600&f=webp&q=80"
  alt="Product"
  width="800"
  height="600"
  loading="lazy"
>
```

---

## Rendering Performance

### React optimization

```javascript
// GOOD: Memoize expensive component to prevent unnecessary re-renders
const ExpensiveList = React.memo(function ExpensiveList({ items, onSelect }) {
  return (
    <ul>
      {items.map(item => (
        <ListItem key={item.id} item={item} onSelect={onSelect} />
      ))}
    </ul>
  );
});
```

```javascript
// BAD: Component re-renders on every parent render, even with same props
function ExpensiveList({ items, onSelect }) {
  return (
    <ul>
      {items.map(item => (
        <ListItem key={item.id} item={item} onSelect={onSelect} />
      ))}
    </ul>
  );
}
```

```javascript
// GOOD: Memoize expensive computation and stabilize callback references
function Dashboard({ data }) {
  const processedData = useMemo(() => {
    return data.map(transformExpensively).sort(byCriteria);
  }, [data]);

  const handleClick = useCallback((id) => {
    navigateTo(`/detail/${id}`);
  }, []);

  return <ExpensiveList items={processedData} onSelect={handleClick} />;
}
```

```javascript
// BAD: New array and function created on every render — children always re-render
function Dashboard({ data }) {
  const processedData = data.map(transformExpensively).sort(byCriteria);
  const handleClick = (id) => navigateTo(`/detail/${id}`);

  return <ExpensiveList items={processedData} onSelect={handleClick} />;
}
```

### Virtual scrolling for large lists

Rendering thousands of DOM elements destroys performance. Virtualization renders only visible items.

```javascript
// GOOD: Virtualized list with @tanstack/react-virtual
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualList({ items }) {
  const parentRef = useRef(null);
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
    overscan: 5,
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: `${virtualRow.start}px`,
              height: `${virtualRow.size}px`,
              width: '100%',
            }}
          >
            {items[virtualRow.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}
```

```javascript
// BAD: Rendering 10,000 items directly into the DOM
function NaiveList({ items }) {
  return (
    <ul>
      {items.map(item => (
        <li key={item.id}>{item.name}</li>
      ))}
    </ul>
  );
}
```

### Vue optimization

```javascript
// GOOD: Vue computed property — cached, only recalculates when dependencies change
export default {
  computed: {
    filteredItems() {
      return this.items.filter(item => item.active).sort((a, b) => a.name.localeCompare(b.name));
    },
  },
};
```

```javascript
// BAD: Method called in template — recalculates on every render
export default {
  methods: {
    getFilteredItems() {
      return this.items.filter(item => item.active).sort((a, b) => a.name.localeCompare(b.name));
    },
  },
};
```

```html
<!-- GOOD: v-once for static content that never changes -->
<footer v-once>
  <p>Copyright 2025 Acme Corp. All rights reserved.</p>
</footer>
```

### General rendering best practices

**Avoid layout thrashing:**

```javascript
// GOOD: Batch DOM reads, then batch DOM writes
function updateElements(elements) {
  // Read phase — all reads first
  const heights = elements.map(el => el.offsetHeight);

  // Write phase — all writes after
  elements.forEach((el, i) => {
    el.style.height = `${heights[i] * 2}px`;
  });
}
```

```javascript
// BAD: Interleaving reads and writes forces layout recalculation each iteration
function updateElements(elements) {
  elements.forEach(el => {
    const height = el.offsetHeight;      // read — triggers layout
    el.style.height = `${height * 2}px`; // write — invalidates layout
  });
}
```

**Use `requestAnimationFrame` for visual updates:**

```javascript
// GOOD: Defer visual updates to the next animation frame
function onScroll() {
  requestAnimationFrame(() => {
    updateScrollIndicator();
    updateParallaxPositions();
  });
}
```

**Use `IntersectionObserver` instead of scroll listeners:**

```javascript
// GOOD: IntersectionObserver for lazy-loading or animations on scroll
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { rootMargin: '100px' }
);

document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));
```

```javascript
// BAD: Scroll event listener without throttling — fires hundreds of times per second
window.addEventListener('scroll', () => {
  document.querySelectorAll('.animate-on-scroll').forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight) {
      el.classList.add('visible');
    }
  });
});
```

---

## Font Loading

### `font-display` strategies

| Value | Behavior | Best for |
|-------|----------|----------|
| `swap` | Show fallback immediately, swap when font loads | Body text — avoids invisible text |
| `optional` | Show fallback, use custom font only if already cached | Performance-critical pages |
| `fallback` | Short block period (100ms), then fallback | Balance between FOUT and FOIT |
| `block` | Invisible text until font loads (up to 3s) | Icon fonts only |

```css
/* GOOD: font-display: swap prevents invisible text */
@font-face {
  font-family: 'CustomFont';
  src: url('/fonts/custom.woff2') format('woff2');
  font-display: swap;
  font-weight: 100 900;
}
```

```css
/* BAD: No font-display — browser default may hide text for up to 3 seconds */
@font-face {
  font-family: 'CustomFont';
  src: url('/fonts/custom.woff2') format('woff2');
}
```

### Font preloading

```html
<!-- GOOD: Preload critical font to reduce FOUT duration -->
<link rel="preload" as="font" type="font/woff2"
      href="/fonts/custom.woff2" crossorigin>
```

### Variable fonts

Variable fonts replace multiple font files (regular, bold, italic) with a single file, reducing total download size.

```css
/* GOOD: Single variable font file replaces 4+ static files */
@font-face {
  font-family: 'Inter';
  src: url('/fonts/Inter-Variable.woff2') format('woff2-variations');
  font-display: swap;
  font-weight: 100 900;
}
```

### Font subsetting

Remove unused characters from font files to reduce size. Particularly impactful for CJK fonts or icon fonts.

```bash
# Subset font to Latin characters only (~100KB -> ~20KB)
pyftsubset CustomFont.woff2 \
  --output-file=CustomFont-latin.woff2 \
  --flavor=woff2 \
  --unicodes="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+2000-206F"
```

---

## Third-Party Script Management

### `async` vs `defer`

| Attribute | Download | Execution | Order preserved | Best for |
|-----------|----------|-----------|-----------------|----------|
| (none) | Blocks parsing | Blocks parsing | Yes | Never — always use async or defer |
| `async` | Parallel | As soon as downloaded (blocks parsing) | No | Analytics, ads — independent scripts |
| `defer` | Parallel | After HTML parsing, before `DOMContentLoaded` | Yes | Libraries that depend on DOM or each other |
| `type="module"` | Parallel | After HTML parsing (deferred by default) | Yes | Modern ES module scripts |

```html
<!-- GOOD: Defer non-critical scripts -->
<script src="/analytics.js" defer></script>
<script src="/chat-widget.js" async></script>
```

```html
<!-- BAD: Render-blocking scripts in <head> -->
<head>
  <script src="/analytics.js"></script>
  <script src="/chat-widget.js"></script>
</head>
```

### Partytown — run third-party scripts in a Web Worker

Partytown moves third-party scripts off the main thread entirely, eliminating their impact on INP and LCP.

```html
<!-- GOOD: Run Google Tag Manager in a worker via Partytown -->
<script>
  partytown = { forward: ['dataLayer.push'] };
</script>
<script src="/~partytown/partytown.js"></script>
<script type="text/partytown" src="https://www.googletagmanager.com/gtag/js?id=GA_ID"></script>
```

### Facade pattern

Lazy-load heavy embeds (YouTube, social widgets, chat) by showing a static placeholder until the user interacts.

```javascript
// GOOD: Facade pattern — load YouTube player only on click
function YouTubeFacade({ videoId, title }) {
  const [isLoaded, setIsLoaded] = useState(false);

  if (isLoaded) {
    return (
      <iframe
        src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
        title={title}
        allow="autoplay"
        style={{ width: '100%', aspectRatio: '16/9', border: 'none' }}
      />
    );
  }

  return (
    <button
      onClick={() => setIsLoaded(true)}
      style={{ position: 'relative', width: '100%', aspectRatio: '16/9' }}
      aria-label={`Play: ${title}`}
    >
      <img
        src={`https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`}
        alt={title}
        loading="lazy"
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />
      <PlayIcon />
    </button>
  );
}
```

```html
<!-- BAD: YouTube iframe loaded immediately — downloads ~800KB of scripts -->
<iframe src="https://www.youtube.com/embed/VIDEO_ID"
        width="560" height="315" frameborder="0"></iframe>
```

### Third-party performance budgets

Set explicit limits on what third-party scripts can cost.

| Budget | Target | How to enforce |
|--------|--------|----------------|
| Total third-party JS | < 100KB gzipped | `bundlesize` or Lighthouse CI |
| Third-party main thread time | < 250ms | Lighthouse third-party audit |
| Number of third-party domains | < 5 | CSP `connect-src` policy |
| Third-party request count | < 10 | Network waterfall review |

---

## API Response Optimization

### Pagination patterns

| Pattern | How | Best for | Drawback |
|---------|-----|----------|----------|
| **Offset** | `?offset=20&limit=10` | Small datasets, simple UIs | Slow for large offsets — `OFFSET 100000` scans rows |
| **Cursor/Keyset** | `?cursor=eyJpZCI6MTAwfQ&limit=10` | Large datasets, real-time feeds | Cannot jump to arbitrary page |
| **Page number** | `?page=3&per_page=10` | Simple UIs with page count | Same offset problem internally |

```javascript
// GOOD: Cursor-based pagination — consistent O(1) performance
app.get('/api/items', async (req, res) => {
  const { cursor, limit = 20 } = req.query;
  const where = cursor ? { id: { gt: decodeCursor(cursor) } } : {};

  const items = await db.item.findMany({
    where,
    take: limit + 1,
    orderBy: { id: 'asc' },
  });

  const hasNext = items.length > limit;
  const data = hasNext ? items.slice(0, -1) : items;

  res.json({
    data,
    next_cursor: hasNext ? encodeCursor(data[data.length - 1].id) : null,
  });
});
```

```javascript
// BAD: Offset pagination degrades at scale
app.get('/api/items', async (req, res) => {
  const { page = 1, per_page = 20 } = req.query;
  // OFFSET 100000 scans and discards 100,000 rows
  const items = await db.item.findMany({
    skip: (page - 1) * per_page,
    take: per_page,
  });
  res.json({ data: items, page });
});
```

### Sparse fieldsets

Return only the fields the client needs.

```javascript
// GOOD: Allow clients to request specific fields
// GET /api/users?fields=id,name,email
app.get('/api/users', async (req, res) => {
  const fields = req.query.fields?.split(',') || null;
  const select = fields
    ? Object.fromEntries(fields.map(f => [f, true]))
    : undefined;

  const users = await db.user.findMany({ select });
  res.json({ data: users });
});
```

```javascript
// BAD: Always return all fields, including large blobs
app.get('/api/users', async (req, res) => {
  const users = await db.user.findMany(); // returns avatar_blob, full_bio, etc.
  res.json({ data: users });
});
```

### Response compression

```javascript
// GOOD: Express with compression middleware (gzip + brotli)
import compression from 'compression';

app.use(compression({
  threshold: 1024,   // Only compress responses > 1KB
  level: 6,          // Balance between speed and compression ratio
  filter: (req, res) => {
    if (req.headers['x-no-compression']) return false;
    return compression.filter(req, res);
  },
}));
```

```nginx
# GOOD: Nginx with Brotli + gzip
brotli on;
brotli_types application/json text/plain text/css application/javascript;
brotli_comp_level 6;

gzip on;
gzip_types application/json text/plain text/css application/javascript;
gzip_min_length 1024;
```

### GraphQL depth and cost limiting

```javascript
// GOOD: Limit query depth and complexity to prevent abuse
import depthLimit from 'graphql-depth-limit';
import { createComplexityLimitRule } from 'graphql-validation-complexity';

const server = new ApolloServer({
  typeDefs,
  resolvers,
  validationRules: [
    depthLimit(5),
    createComplexityLimitRule(1000, {
      scalarCost: 1,
      objectCost: 10,
      listFactor: 20,
    }),
  ],
});
```

### Batch endpoints

```javascript
// GOOD: Batch endpoint to reduce round-trips
// POST /api/batch
// Body: { "requests": [{ "method": "GET", "path": "/users/1" }, { "method": "GET", "path": "/users/2" }] }
app.post('/api/batch', async (req, res) => {
  const results = await Promise.all(
    req.body.requests.map(r => handleRequest(r.method, r.path, r.body))
  );
  res.json({ responses: results });
});
```

### ETags and conditional requests

```javascript
// GOOD: ETag support for conditional requests — respond with 304 when unchanged
import etag from 'etag';

app.get('/api/products/:id', async (req, res) => {
  const product = await db.product.findUnique({ where: { id: req.params.id } });
  const body = JSON.stringify(product);
  const tag = etag(body);

  res.set('ETag', tag);
  res.set('Cache-Control', 'private, max-age=0, must-revalidate');

  if (req.headers['if-none-match'] === tag) {
    return res.status(304).end(); // Not Modified — saves bandwidth
  }

  res.json(product);
});
```

---

## Performance Tools

| Tool | What it measures | When to use |
|------|-----------------|-------------|
| **Lighthouse** | Core Web Vitals, accessibility, best practices, SEO | Development and CI — synthetic audit |
| **WebPageTest** | Multi-location real browser performance, filmstrip, waterfall | Pre-release validation, competitor comparison |
| **bundlephobia** | npm package size (gzip, tree-shaken) | Before adding a dependency |
| **webpack-bundle-analyzer** | Bundle composition treemap | After build — identify large modules |
| **source-map-explorer** | Bundle size breakdown by source file | After build — granular size analysis |
| **Chrome DevTools Performance** | Runtime CPU, memory, rendering, network | Debugging specific slowness |
| **react-scan** | React component render counts and timing | Debugging React re-render issues |
| **Chrome User Experience Report (CrUX)** | Real user Core Web Vitals data | Measuring production performance |
| **Sentry Performance** | Real user transaction tracing with Web Vitals | Production monitoring and alerting |
| **`@next/bundle-analyzer`** | Next.js bundle composition | Next.js projects specifically |

### Using Lighthouse in CI

```yaml
# .github/workflows/lighthouse.yml
- name: Lighthouse CI
  uses: treosh/lighthouse-ci-action@v12
  with:
    urls: |
      http://localhost:3000/
      http://localhost:3000/dashboard
    budgetPath: ./lighthouse-budget.json
    temporaryPublicStorage: true
```

---

## Performance Budgets

### Defining budgets

| Metric | Budget | Rationale |
|--------|--------|-----------|
| Initial JS bundle | < 200KB gzipped | Keep parse + compile time under 1s on mid-range mobile |
| Total page weight | < 1MB (initial load) | Usable on 3G connections within 5s |
| LCP | < 2.5s | Core Web Vital threshold for "good" |
| INP | < 200ms | Core Web Vital threshold for "good" |
| CLS | < 0.1 | Core Web Vital threshold for "good" |
| Third-party JS | < 100KB gzipped | Limit impact of external scripts |
| Image per asset | < 200KB | Responsive images should be appropriately sized |
| Web font files | < 100KB total | Subset and use variable fonts |

### Enforcing budgets in CI

**bundlesize:**

```json
// package.json
{
  "bundlesize": [
    { "path": "dist/main.*.js", "maxSize": "200 kB" },
    { "path": "dist/vendor.*.js", "maxSize": "150 kB" },
    { "path": "dist/**/*.css", "maxSize": "50 kB" }
  ]
}
```

**Lighthouse CI budget:**

```json
// lighthouse-budget.json
[
  {
    "path": "/*",
    "timings": [
      { "metric": "largest-contentful-paint", "budget": 2500 },
      { "metric": "interactive", "budget": 3800 },
      { "metric": "cumulative-layout-shift", "budget": 0.1 }
    ],
    "resourceSizes": [
      { "resourceType": "script", "budget": 200 },
      { "resourceType": "total", "budget": 1000 }
    ]
  }
]
```

**webpack performance hints:**

```javascript
// webpack.config.js
module.exports = {
  performance: {
    maxAssetSize: 250000,       // 250KB per asset
    maxEntrypointSize: 250000,  // 250KB per entrypoint
    hints: 'error',             // Fail the build if exceeded
  },
};
```

---

## Best Practices

- Measure before optimizing — use Lighthouse, CrUX, or RUM to identify actual bottlenecks, not assumed ones
- Preload the LCP element (image, font, or critical resource) with `<link rel="preload">`
- Use `loading="lazy"` on all below-fold images and `fetchpriority="high"` on the LCP image
- Code-split by route at minimum — use dynamic `import()` for heavy components
- Set explicit `width` and `height` on all images and embeds to prevent CLS
- Use `font-display: swap` and preload critical fonts to avoid invisible text
- Serve images in WebP/AVIF with `<picture>` fallback chains
- Use cursor-based pagination for large datasets — offset pagination degrades at scale
- Enable gzip/brotli compression on all text-based API responses
- Define and enforce performance budgets in CI — budgets that are not enforced are ignored

## Anti-Patterns

- Loading all JavaScript in a single bundle without code splitting
- Static imports of large libraries (`lodash`, `moment`, `chart.js`) used in one component
- Images without `width`/`height` attributes — causes layout shifts (CLS)
- Synchronous `<script>` tags in `<head>` without `async` or `defer`
- Rendering thousands of list items without virtualization
- Interleaving DOM reads and writes in loops (layout thrashing)
- Loading YouTube/Twitter/chat embeds eagerly instead of using facade pattern
- No `font-display` declaration — browser may hide text for up to 3 seconds
- Returning all database fields in API responses when clients need a subset
- Offset-based pagination on large tables without keyset alternative
- No performance budgets — bundle size grows unchecked over time
- Third-party scripts loaded synchronously on the main thread
