// 内链 404 扫描：检查 dist/ 里所有内部链接是否指向存在的页面。
// 用法：node scripts/link-check.mjs（build 后跑；发现死链退出码非零）
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(fileURLToPath(import.meta.url), '..', '..');
const dist = join(root, 'dist');

function walk(dir, files = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, files);
    else if (name.endsWith('.html')) files.push(p);
  }
  return files;
}

// 目录式输出（/about/index.html）→ 路由 /about 或 /about/；根 index.html → /
function routeOf(file) {
  let rel = file.slice(dist.length).replace(/\\/g, '/');
  rel = rel.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
  return rel === '' ? '/' : rel;
}

const routes = new Set(walk(dist).map(routeOf));

// 所有已存在的静态文件（favicon / css / 图片等）也算可达
const files = new Set();
(function collect(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) collect(p);
    else files.add(p.slice(dist.length).replace(/\\/g, '/'));
  }
})(dist);

// 重定向/meta-refresh 也算可达
const okTarget = (t) => {
  const clean = t.split('#')[0].split('?')[0];
  if (clean === '' || clean === '/') return true;
  if (files.has(clean)) return true;
  if (routes.has(clean)) return true;
  if (routes.has(clean.endsWith('/') ? clean.slice(0, -1) : clean + '/')) return true;
  return false;
};

const HREF_RE = /(?:href|src)=["']([^"']+)["']/g;
const broken = [];
let checked = 0;

for (const file of walk(dist)) {
  const html = readFileSync(file, 'utf8');
  const route = routeOf(file);
  for (const m of html.matchAll(HREF_RE)) {
    let target = m[1];
    if (/^(https?:|mailto:|tel:|#|data:|javascript:)/i.test(target)) continue;
    // 站外相对协议统一走绝对地址，跳过
    if (target.startsWith('//')) continue;
    checked++;
    if (!target.startsWith('/')) {
      // 相对路径
      target = new URL(target, 'http://x' + (route.endsWith('/') ? route : route + '/')).pathname;
    }
    if (!okTarget(target)) {
      broken.push(`${route} → ${m[1]}`);
    }
  }
}

console.log(`扫描 ${routes.size} 个路由，检查 ${checked} 个内部链接`);
if (broken.length) {
  console.error(`发现 ${broken.length} 个死链：`);
  for (const b of broken) console.error('  ' + b);
  process.exit(1);
} else {
  console.log('零死链 ✓');
}
