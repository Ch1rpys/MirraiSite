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

async function fetchChecksums(assets) {
  // 发版 CI 附带校验和：<file>.sha256 或聚合的 SHA256SUMS；解析成 { 文件名: 哈希 }
  const sums = {};
  for (const a of assets) {
    if (!a.name.endsWith('.sha256') && a.name !== 'SHA256SUMS') continue;
    try {
      const res = await fetch(a.downloadUrl);
      if (!res.ok) continue;
      const text = await res.text();
      if (a.name === 'SHA256SUMS') {
        for (const line of text.split('\n')) {
          const m = line.trim().split(/\s+/);
          if (m[0] && /^[0-9a-f]{64}$/i.test(m[0]) && m[1]) {
            sums[m[1].replace(/^.*\//, '')] = m[0];
          }
        }
      } else {
        const m = text.trim().split(/\s+/);
        if (m[0] && /^[0-9a-f]{64}$/i.test(m[0])) {
          sums[m[1] ? m[1].replace(/^.*\//, '') : a.name.replace(/\.sha256$/, '')] = m[0];
        }
      }
    } catch {
      /* 单个校验和失败不影响整体 */
    }
  }
  return sums;
}

async function normalize(raw) {
  const assets = (raw.assets || []).map((a) => ({
    name: a.name,
    size: a.size,
    downloadUrl: a.browser_download_url,
  }));
  return {
    version: raw.tag_name,
    name: raw.name || raw.tag_name,
    publishedAt: raw.published_at,
    prerelease: raw.prerelease,
    htmlUrl: raw.html_url,
    body: raw.body || '',
    assets,
    checksums: await fetchChecksums(assets),
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
  const releases = await Promise.all(raw.map(normalize));

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
