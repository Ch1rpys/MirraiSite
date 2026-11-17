// 三维房间的一条龙：取贴图 → Blender 搭场景 / 渲染静帧 / 烘焙 → 压图集。
// 用法：
//   npm run room                 全部重做（静帧 + 烘焙）
//   npm run room -- preview      只出小样（.cache/room/preview-*.jpg），调场景时用
//   npm run room -- stills       只重渲静帧
//   npm run room -- bake         只重烘实时三维层（图集 + 网格 + scene.json）
//   npm run room -- json         只重写 scene.json（只改了裁切对准点这类不影响画面的参数时，几秒）
//   加 --from-blend              不重建场景，直接用 assets/room/room.blend（在 Blender 里手工改过之后）
// Blender 的位置：环境变量 BLENDER，否则找 macOS 默认安装位置，再否则用 PATH 里的 blender。
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(fileURLToPath(import.meta.url), '..', '..', '..');
const args = process.argv.slice(2);
const steps = args.filter((a) => !a.startsWith('--'));
if (steps.length === 0) args.unshift('stills', 'bake');

const macDefault = '/Applications/Blender.app/Contents/MacOS/Blender';
const blender = process.env.BLENDER || (existsSync(macDefault) ? macDefault : 'blender');

function run(cmd, cmdArgs) {
  const r = spawnSync(cmd, cmdArgs, { cwd: root, stdio: 'inherit' });
  if (r.error) {
    console.error(`运行失败：${cmd}（${r.error.message}）`);
    process.exit(1);
  }
  if (r.status !== 0) process.exit(r.status ?? 1);
}

run(process.execPath, [join('scripts', 'room', 'fetch-textures.mjs')]);
run(blender, ['-b', '--factory-startup', '-P', join('scripts', 'room', 'build.py'), '--', ...args]);
if (args.includes('bake')) run(process.execPath, [join('scripts', 'room', 'pack-atlases.mjs')]);
