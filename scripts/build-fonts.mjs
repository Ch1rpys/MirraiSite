// 构建自托管字体：
//  1) 可变字体按实际用重实例化（去 gvar 开销）
//  2) Latin 整表转 woff2；中文按站点实际用字子集化
// 用法：node scripts/build-fonts.mjs
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, readdirSync, statSync, writeFileSync, existsSync } from 'node:fs';
import { join, extname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(fileURLToPath(import.meta.url), '..', '..');
const cacheDir = join(root, '.cache', 'fonts');
const outDir = join(root, 'public', 'fonts');
mkdirSync(outDir, { recursive: true });
mkdirSync(cacheDir, { recursive: true });

// 源字体（可变） → 实例化权重 → 输出
const FONTS = [
  {
    source: join(root, 'assets/logo-drafts/fonts/CormorantGaramond.ttf'),
    instance: join(cacheDir, 'CormorantGaramond-inst.ttf'),
    weight: 'wght=550',
    out: 'CormorantGaramond.woff2',
    cjk: false,
  },
  {
    source: join(root, 'assets/logo-drafts/fonts/PlayfairDisplay.ttf'),
    instance: join(cacheDir, 'PlayfairDisplay-inst.ttf'),
    weight: 'wght=500',
    out: 'PlayfairDisplay.woff2',
    cjk: false,
  },
  {
    source: join(root, 'assets/logo-drafts/fonts/EBGaramond.ttf'),
    instance: join(cacheDir, 'EBGaramond-inst.ttf'),
    weight: 'wght=400',
    out: 'EBGaramond.woff2',
    cjk: false,
  },
  {
    source: join(cacheDir, 'NotoSansSC-VF.ttf'),
    instance: join(cacheDir, 'NotoSansSC-400-inst.ttf'),
    weight: 'wght=400',
    out: 'NotoSansSC-Subset.woff2',
    cjk: true,
  },
];

for (const f of FONTS) {
  if (!existsSync(f.source)) {
    console.error(`缺少 ${relative(root, f.source)}`);
    process.exit(1);
  }
}

// ---- 扫描站点用字 ----
const SCAN_DIRS = ['src'];
const SCAN_EXT = new Set(['.astro', '.tsx', '.ts', '.js', '.mjs', '.json', '.mdx', '.md', '.html']);
const IGNORE_DIR = new Set(['node_modules', 'dist', '.astro', '.git']);

function walk(dir, files = []) {
  for (const name of readdirSync(dir)) {
    if (IGNORE_DIR.has(name)) continue;
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, files);
    else if (SCAN_EXT.has(extname(name))) files.push(p);
  }
  return files;
}

const CJK_RE =
  /[\u3000-\u303F\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF\u2018-\u201F\u2026\u2014\u00B7]/g;

const chars = new Set();
for (const dir of SCAN_DIRS) {
  const abs = join(root, dir);
  if (!existsSync(abs)) continue;
  for (const file of walk(abs)) {
    const text = readFileSync(file, 'utf8');
    for (const ch of text.match(CJK_RE) ?? []) chars.add(ch);
  }
}
for (const ch of ' \u3000\u3001\u3002\uFF0C\uFF01\uFF1F\uFF1A\uFF1B\uFF08\uFF09\u300A\u300B\u2014\u2026\u00B7') {
  chars.add(ch);
}

const textFile = join(cacheDir, 'subset-chars.txt');
writeFileSync(textFile, [...chars].join(''), 'utf8');
console.log(`扫描到 ${chars.size} 个唯一用字 → ${relative(root, textFile)}`);

// ---- 实例化 + 压缩 ----
for (const f of FONTS) {
  if (!existsSync(f.instance)) {
    execFileSync('python3', ['-m', 'fontTools.varLib.instancer', f.source, f.weight, '-o', f.instance], {
      stdio: ['ignore', 'ignore', 'inherit'],
    });
    console.log(`实例化 ${relative(root, f.instance)}`);
  }

  const out = join(outDir, f.out);
  if (f.cjk) {
    execFileSync(
      'python3',
      [
        '-m',
        'fontTools.subset',
        f.instance,
        `--text-file=${textFile}`,
        '--output-file=' + out,
        '--flavor=woff2',
        '--unicodes=U+0020-007E', // ASCII 一并保留，中英混排字形一致
        '--layout-features=*',
        '--notdef-glyph',
        '--notdef-outline',
        '--recommended-glyphs',
        '--name-IDs=*',
        '--name-legacy',
      ],
      { stdio: ['ignore', 'ignore', 'inherit'] }
    );
  } else {
    // Latin：按站点用字 + ASCII 子集化（字标/标题只需少量字形）
    execFileSync(
      'python3',
      [
        '-m',
        'fontTools.subset',
        f.instance,
        `--text-file=${textFile}`,
        '--output-file=' + out,
        '--flavor=woff2',
        '--unicodes=U+0020-007E,U+00A0,U+2018-201F,U+2026',
        '--layout-features=*',
        '--notdef-glyph',
        '--notdef-outline',
        '--recommended-glyphs',
        '--name-IDs=*',
        '--name-legacy',
      ],
      { stdio: ['ignore', 'ignore', 'inherit'] }
    );
  }
  const size = statSync(out).size;
  console.log(`${f.out} = ${(size / 1024).toFixed(1)} KB`);
}
