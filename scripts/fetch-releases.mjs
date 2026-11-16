// 构建时拉取 GitHub Releases（下载页数据）。
// 失败时降级用上次缓存数据，不阻断构建。
// 用法：node scripts/fetch-releases.mjs（package.json 的 build 会先跑它）
import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(fileURLToPath(import.meta.url), '..', '..');
const outDir = join(root, 'src', 'data');
const outFile = join(outDir, 'releases.json');

const API = 'https://api.github.com/repos/Ch1rpys/Mirrai/releases?per_page=20';

function normalize(raw) {
  return {
    version: raw.tag_name,
    name: raw.name || raw.tag_name,
    publishedAt: raw.published_at,
    prerelease: raw.prerelease,
    htmlUrl: raw.html_url,
    body: raw.body || '',
    assets: (raw.assets || []).map((a) => ({
      name: a.name,
      size: a.size,
      downloadUrl: a.browser_download_url,
    })),
  };
}

try {
  const res = await fetch(API, {
    headers: {
      Accept: 'application/vnd.github+json',
      'User-Agent': 'mirrai-site-build',
      ...(process.env.GITHUB_TOKEN ? { Authorization: `Bearer ${process.env.GITHUB_TOKEN}` } : {}),
    },
  });
  if (!res.ok) throw new Error(`GitHub API ${res.status}`);
  const raw = await res.json();
  const releases = raw.map(normalize);

  mkdirSync(outDir, { recursive: true });
  writeFileSync(outFile, JSON.stringify({ fetchedAt: new Date().toISOString(), releases }, null, 2));
  console.log(`fetched ${releases.length} releases → src/data/releases.json`);
} catch (err) {
  if (existsSync(outFile)) {
    console.warn(`[fetch-releases] 失败，沿用缓存数据：${err.message}`);
  } else {
    // 无缓存也不能阻断构建：写空列表，下载页显示「版本信息暂不可用」
    mkdirSync(outDir, { recursive: true });
    writeFileSync(outFile, JSON.stringify({ fetchedAt: null, releases: [] }, null, 2));
    console.warn(`[fetch-releases] 失败且无缓存，写入空数据：${err.message}`);
  }
}
