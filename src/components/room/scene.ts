/**
 * 房间场景的数据（scripts/room/build.py 从 Blender 场景导出）：机位、裁切对准点、灯在画面里的位置、
 * 2.5D 退路的推镜参数。静帧、CSS 和实时三维层都读这一份，所以互相对得上。
 */
import data from '../../assets/room/scene.json';

export const scene = data;

/** 一个镜头有横、竖两幅构图：横屏用 l，竖屏（手机）用 p */
export type Shot = 'wide' | 'close';

const CAM = {
  wide: { l: 'wide', p: 'wideP' },
  close: { l: 'close', p: 'closeP' },
} as const;

/** 与 CSS、<source media> 共用的竖屏条件 */
export const PORTRAIT = '(max-aspect-ratio: 1/1)';

/** `.scene-cover` 的 CSS 变量：两幅构图各自的画幅比、铺满时对准的点、灯的位置 */
export function coverVars(shot: Shot): string {
  const vars: string[] = [];
  for (const o of ['l', 'p'] as const) {
    const cam = CAM[shot][o];
    const crop = data.crop[cam];
    const lamp = data.stills[cam].lamp;
    vars.push(
      `--ar-${o}:${data.cams[cam].aspect}`,
      `--zoom-${o}:${crop.zoom}`,
      `--fx-${o}:${crop.fx}`,
      `--fy-${o}:${crop.fy}`,
      `--lx-${o}:${lamp[0]}`,
      `--ly-${o}:${lamp[1]}`,
    );
  }
  return vars.join(';');
}

/**
 * 横幅构图里照片盒子的铺法，加上信纸左缘在照片里的位置（--letter-x0）。
 * 叠在照片上的文字栏用它算出信纸在视口里的位置，好让开它（见 Hero.astro）。
 */
export function letterVars(shot: Shot): string {
  const cam = CAM[shot].l;
  const crop = data.crop[cam];
  return [
    `--ar:${data.cams[cam].aspect}`,
    `--zoom:${crop.zoom}`,
    `--fx:${crop.fx}`,
    `--letter-x0:${data.stills[cam].letterBox[0]}`,
  ].join(';');
}

/** 2.5D 推镜（三维层不可用时的退路）：远景绕 (ox, oy) 放大到 scale */
export function pushVars(): string {
  const vars: string[] = [];
  for (const o of ['l', 'p'] as const) {
    const p = data.push[o];
    vars.push(`--push-${o}:${p.scale}`, `--ox-${o}:${p.ox}`, `--oy-${o}:${p.oy}`);
  }
  return vars.join(';');
}
