// 三维房间用到的 CC0 贴图（Poly Haven，https://polyhaven.com/license —— CC0，无需署名）。
// 只在本地搭建/烘焙场景时用，下载到 .cache/room/textures（不入库、不随站点发布）。
// 用法：node scripts/room/fetch-textures.mjs
import { mkdirSync, existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(fileURLToPath(import.meta.url), '..', '..', '..');
const outDir = join(root, '.cache', 'room', 'textures');
mkdirSync(outDir, { recursive: true });

/** [asset id, map, resolution] —— map: diff | rough | disp */
const FILES = [
  ['wood_table_001', 'diff', '4k'], // 书桌桌面
  ['wood_table_001', 'rough', '2k'],
  ['wood_table_001', 'disp', '2k'],
  ['walnut_veneer', 'diff', '2k'], // 桌腿 / 椅子 / 书架
  ['walnut_veneer', 'rough', '2k'],
  ['walnut_veneer', 'disp', '2k'],
  ['wood_floor_worn', 'diff', '2k'], // 地板
  ['wood_floor_worn', 'rough', '2k'],
  ['wood_floor_worn', 'disp', '2k'],
  ['plastered_wall_04', 'diff', '2k'], // 墙面
  ['plastered_wall_04', 'rough', '2k'],
  ['plastered_wall_04', 'disp', '2k'],
  ['knitted_fleece', 'diff', '1k'], // 床上的毯子
  ['knitted_fleece', 'disp', '1k'],
  ['rough_linen', 'diff', '1k'], // 窗帘
  ['rough_linen', 'disp', '1k'],
];

let fetched = 0;
for (const [id, map, res] of FILES) {
  const name = `${id}_${map}_${res}.jpg`;
  const dest = join(outDir, name);
  if (existsSync(dest)) continue;
  const url = `https://dl.polyhaven.org/file/ph-assets/Textures/jpg/${res}/${id}/${name}`;
  const r = await fetch(url, { headers: { 'User-Agent': 'mirrai-site-build' } });
  if (!r.ok) {
    console.error(`下载失败 ${r.status}：${url}`);
    process.exit(1);
  }
  writeFileSync(dest, Buffer.from(await r.arrayBuffer()));
  fetched++;
  console.log(`✓ ${name}`);
}
console.log(`贴图就位：${FILES.length} 个（本次下载 ${fetched} 个）→ .cache/room/textures`);
