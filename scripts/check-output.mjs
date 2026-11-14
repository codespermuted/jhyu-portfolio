import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Check the generated site, including deployments under a URL prefix.
// Run after `npm run build`; BASE_PATH may be supplied or inferred from canonical.
const projectRoot = fileURLToPath(new URL('../', import.meta.url));
const outputRoot = path.resolve(projectRoot, process.env.OUTPUT_DIR || 'dist');
const failures = [];
const fail = (message) => failures.push(message);
const relative = (file) => path.relative(outputRoot, file).split(path.sep).join('/');

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const file = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(file) : [file];
  }));
  return nested.flat();
}

function decodeEntities(value) {
  return value.replace(/&#x([\da-f]+);|&#(\d+);|&(amp|quot|apos|lt|gt);/gi, (whole, hex, decimal, name) => {
    if (hex || decimal) return String.fromCodePoint(parseInt(hex || decimal, hex ? 16 : 10));
    return { amp: '&', quot: '"', apos: "'", lt: '<', gt: '>' }[name.toLowerCase()] || whole;
  });
}

function tags(html) {
  const clean = html.replace(/<!--[\s\S]*?-->/g, '')
    .replace(/(<script\b[^>]*>)[\s\S]*?<\/script\s*>/gi, '$1</script>')
    .replace(/(<style\b[^>]*>)[\s\S]*?<\/style\s*>/gi, '$1</style>');
  return [...clean.matchAll(/<([a-z][\w:-]*)\b((?:"[^"]*"|'[^']*'|[^'">])*)>/gi)].map((match) => {
    const attributes = Object.create(null);
    for (const part of match[2].matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g)) {
      attributes[part[1].toLowerCase()] = decodeEntities(part[2] ?? part[3] ?? part[4] ?? '');
    }
    return { name: match[1].toLowerCase(), attributes };
  });
}

let files;
try {
  files = await walk(outputRoot);
} catch {
  console.error('FAIL: Build output is missing. Run npm run build first.');
  process.exit(1);
}

const htmlFiles = files.filter((file) => file.endsWith('.html'));
const documents = new Map();
const sizes = new Map();
let largestHtml = 0;
let inlineJsBytes = 0;
let externalLinks = 0;
let imageCount = 0;
let localReferences = 0;

for (const file of files) {
  const size = (await stat(file)).size;
  sizes.set(file, size);
  if (!/\.(?:html|css|js|mjs|json|svg|txt|xml)$/i.test(file)) continue;
  const text = await readFile(file, 'utf8');
  if (/\uFEFF|%EF%BB%BF|&#(?:65279|xFEFF);/i.test(text)) fail(`${relative(file)}: literal or encoded BOM found`);
  if (/data:\s*(?:image|video|audio|font|application|text)\//i.test(text)) fail(`${relative(file)}: embedded data URI asset found`);
  if (!file.endsWith('.html')) continue;
  const parsedTags = tags(text);
  const ids = new Set();
  for (const tag of parsedTags) {
    const id = tag.attributes.id;
    if (id !== undefined) {
      if (ids.has(id)) fail(`${relative(file)}: duplicate id "${id}"`);
      ids.add(id);
    }
  }
  documents.set(file, { text, tags: parsedTags, ids });
  largestHtml = Math.max(largestHtml, size);
  if (size >= 100_000) fail(`${relative(file)}: HTML is ${size} bytes (must be under 100,000)`);
  for (const script of text.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
    if (!/\bsrc\s*=/.test(script[1]) && !/type\s*=\s*["']application\/(?:ld\+)?json["']/i.test(script[1])) {
      inlineJsBytes += Buffer.byteLength(script[2]);
    }
  }
}

const homeFile = path.join(outputRoot, 'index.html');
const homeDocument = documents.get(homeFile);
if (!homeDocument) {
  console.error('FAIL: dist/index.html is missing.');
  process.exit(1);
}
const canonical = homeDocument.tags.find(({ name, attributes }) => name === 'link' && attributes.rel === 'canonical')?.attributes.href;
const site = new URL(process.env.SITE_URL || canonical || 'https://jhyu-portfolio.netlify.app/');
const baseInput = process.env.BASE_PATH ?? (canonical ? new URL(canonical).pathname : '/');
const basePath = `/${baseInput.replace(/^\/+|\/+$/g, '')}`.replace(/\/$/, '');

function deployedUrl(file) {
  const pathname = relative(file).replace(/(^|\/)index\.html$/, '$1');
  return new URL(`${basePath}/${pathname}`, site.origin);
}

async function checkReference(value, sourceFile, label, checkFragment = false) {
  if (!value || value === '#') {
    fail(`${relative(sourceFile)}: empty ${label}`);
    return;
  }
  let target;
  try {
    target = new URL(value, deployedUrl(sourceFile));
  } catch {
    fail(`${relative(sourceFile)}: invalid ${label} ${value}`);
    return;
  }
  if (['mailto:', 'tel:'].includes(target.protocol) && label === 'href') return;
  if (!['https:', 'http:'].includes(target.protocol)) {
    fail(`${relative(sourceFile)}: unsafe or unsupported ${label} scheme ${target.protocol}`);
    return;
  }
  if (target.origin !== site.origin) {
    externalLinks++;
    if (target.protocol !== 'https:') fail(`${relative(sourceFile)}: insecure external ${label} ${value}`);
    return;
  }
  localReferences++;
  let pathname;
  try {
    pathname = decodeURIComponent(target.pathname);
  } catch {
    fail(`${relative(sourceFile)}: invalid encoded URL ${value}`);
    return;
  }
  if (basePath && pathname !== basePath && !pathname.startsWith(`${basePath}/`)) {
    fail(`${relative(sourceFile)}: ${value} escapes deployment base ${basePath}/`);
    return;
  }
  const localPath = pathname.slice(basePath.length).replace(/^\/+/, '');
  const candidate = path.resolve(outputRoot, localPath);
  if (candidate !== outputRoot && !candidate.startsWith(`${outputRoot}${path.sep}`)) {
    fail(`${relative(sourceFile)}: ${value} escapes output directory`);
    return;
  }
  let resolved;
  for (const option of [candidate, path.join(candidate, 'index.html'), `${candidate}.html`]) {
    try {
      if ((await stat(option)).isFile()) { resolved = option; break; }
    } catch { /* Try the next static-route form. */ }
  }
  if (!resolved) {
    fail(`${relative(sourceFile)}: missing ${label} target ${value}`);
    return;
  }
  if (checkFragment && target.hash && documents.has(resolved)) {
    let fragment;
    try { fragment = decodeURIComponent(target.hash.slice(1)); } catch { fragment = target.hash.slice(1); }
    if (!documents.get(resolved).ids.has(fragment)) fail(`${relative(sourceFile)}: missing fragment ${value}`);
  }
}

for (const [file, document] of documents) {
  if (document.tags.filter((tag) => tag.name === 'h1').length !== 1) fail(`${relative(file)}: expected one h1`);
  if (!document.tags.some((tag) => tag.name === 'html' && tag.attributes.lang)) fail(`${relative(file)}: missing page language`);
  for (const { name, attributes } of document.tags) {
    for (const attribute of ['href', 'src', 'poster']) {
      if (attribute in attributes) await checkReference(attributes[attribute], file, attribute, attribute === 'href');
    }
    if (attributes.srcset) {
      for (const candidate of attributes.srcset.split(',')) await checkReference(candidate.trim().split(/\s+/)[0], file, 'srcset');
    }
    if (name === 'img') {
      imageCount++;
      if (!('alt' in attributes)) fail(`${relative(file)}: image lacks alt (${attributes.src})`);
      for (const dimension of ['width', 'height']) {
        if (!/^\d+(?:\.\d+)?$/.test(attributes[dimension] || '') || Number(attributes[dimension]) <= 0) fail(`${relative(file)}: image lacks positive ${dimension} (${attributes.src})`);
      }
    }
    if ((name === 'a' || name === 'area') && attributes.target === '_blank') {
      const rel = new Set((attributes.rel || '').toLowerCase().split(/\s+/));
      if (!rel.has('noopener') || !rel.has('noreferrer')) fail(`${relative(file)}: new-tab link lacks noopener noreferrer (${attributes.href})`);
    }
    if (name === 'video' && file === homeFile && ('autoplay' in attributes || attributes.preload !== 'none')) fail('index.html: homepage video loads eagerly');
    if (name === 'meta' && ['og:image', 'twitter:image'].includes(attributes.property || attributes.name)) await checkReference(attributes.content, file, 'share image');
  }
}

for (const file of files.filter((item) => item.endsWith('.css'))) {
  const css = await readFile(file, 'utf8');
  for (const match of css.matchAll(/url\(\s*(?:"([^"]*)"|'([^']*)'|([^\s)]+))\s*\)/gi)) {
    await checkReference(match[1] ?? match[2] ?? match[3], file, 'CSS url');
  }
}

const projects = JSON.parse(await readFile(path.join(projectRoot, 'src/data/projects.json'), 'utf8'));
const projectRoutes = htmlFiles.filter((file) => /^projects\/[^/]+\/index\.html$/.test(relative(file)));
if (projects.length !== 11 || projectRoutes.length !== 11) fail(`Expected 11 project entries and routes; found ${projects.length} entries and ${projectRoutes.length} routes`);
if (new Set(projects.map((project) => project.slug)).size !== projects.length) fail('Project slugs are not unique');
for (const project of projects) {
  if (!documents.has(path.join(outputRoot, 'projects', project.slug, 'index.html'))) fail(`Missing project route ${project.slug}`);
}

const fontBytes = files.filter((file) => /\.(?:woff2?|ttf|otf)$/i.test(file)).reduce((sum, file) => sum + sizes.get(file), 0);
const scriptBytes = files.filter((file) => /\.(?:js|mjs)$/i.test(file)).reduce((sum, file) => sum + sizes.get(file), 0) + inlineJsBytes;
if (fontBytes >= 200_000) fail(`Fonts total ${fontBytes} bytes (must be under 200,000)`);
if (scriptBytes >= 10_000) fail(`JavaScript totals ${scriptBytes} bytes (must be under 10,000)`);

const metrics = { basePath: basePath || '/', pages: htmlFiles.length, projectRoutes: projectRoutes.length, localReferences, externalLinks, imageCount, largestHtmlBytes: largestHtml, fontBytes, javaScriptBytes: scriptBytes };
console.log(JSON.stringify(metrics, null, 2));
if (failures.length) {
  for (const message of [...new Set(failures)]) console.error(`FAIL: ${message}`);
  process.exitCode = 1;
} else {
  console.log('PASS: static routes, assets, anchors, image metadata, link safety, BOM/data-URI checks and size budgets.');
}
