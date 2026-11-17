// 把 Blender 烘出来的光照图集（.cache/room/atlas-N.png）压成 WebP，放进 src/assets/room3d/：
//   atlas-N.webp     原尺寸，桌面端用
//   atlas-N-1k.webp  半尺寸，手机端用
// 用法：node scripts/room/pack-atlases.mjs（scripts/room/build.py -- bake 之后跑）
import { existsSync, mkdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const root = join(fileURLToPath(import.meta.url), '..', '..', '..');
const cache = join(root, '.cache', 'room');
const out = join(root, 'src', 'assets', 'room3d');
mkdirSync(out, { recursive: true });

const kb = (file) => `${Math.round(statSync(file).size / 1024)} KB`;

for (const i of [0, 1]) {
  const src = join(cache, `atlas-${i}.png`);
  if (!existsSync(src)) {
    console.error(`缺少 ${src}——先跑 scripts/room/build.py -- bake`);
    process.exit(1);
  }
  const { width } = await sharp(src).metadata();
  const full = join(out, `atlas-${i}.webp`);
  const half = join(out, `atlas-${i}-1k.webp`);
  // 图集里岛与岛紧挨着：smartSubsample 减少色度采样带来的串色
  await sharp(src).webp({ quality: 86, effort: 6, smartSubsample: true }).toFile(full);
  await sharp(src)
    .resize(Math.round(width / 2), null, { kernel: 'lanczos3' })
    .webp({ quality: 84, effort: 6, smartSubsample: true })
    .toFile(half);
  console.log(`atlas-${i}: ${width}px → ${kb(full)}；${Math.round(width / 2)}px → ${kb(half)}`);
}
