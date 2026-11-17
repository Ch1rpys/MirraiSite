/**
 * 进门镜头的三维层：Blender 里搭的那间房（光照已烘进图集）+ 一段真的镜头运动。
 *
 * 不依赖三维库：一个无光照着色器、两张图集、两次 draw call，再叠一层灯的光晕。
 * 取景完全跟着页面上的两张静帧走——起点对齐进门静帧的盒子，终点对齐 Hero 照片的盒子，
 * 所以开场接得上、落定后溶进照片也不跳。
 *
 * 任何一步不行（不支持 WebGL2、加载失败、超时）都只是不出现：Base.astro 的时间轴自动退回 2.5D 推镜。
 * 镜头插值必须与 scripts/room/build.py 的 path_cam 一致（看不见的面在导出时已剔除）。
 */
import atlas0Half from '../../assets/room3d/atlas-0-1k.webp?url';
import atlas0 from '../../assets/room3d/atlas-0.webp?url';
import atlas1Half from '../../assets/room3d/atlas-1-1k.webp?url';
import atlas1 from '../../assets/room3d/atlas-1.webp?url';
import meshUrl from '../../assets/room3d/room.bin?url';
import { PORTRAIT, scene } from './scene';

type Vec3 = [number, number, number];
/** 机位：位置、盯着的点、整幅画面的纵向视场角与宽高比 */
type Cam = { pos: number[]; look: number[]; fovY: number; aspect: number };
/** 视口在单位距离处的视锥边界：左、右、下、上 */
type Bounds = [number, number, number, number];

interface IntroControl {
  T: { hold: number; wait: number; push: number; move: number; out: number; outDur: number; copy: number };
  mode: '2d' | '3d';
  want3d: boolean;
  ready(start: () => void): boolean;
  fail(): void;
}

declare global {
  interface Window {
    __intro?: IntroControl;
  }
}

const VERT = `#version 300 es
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec2 aUv;
uniform mat4 uMvp;
uniform vec3 uMin;
uniform vec3 uSize;
out vec2 vUv;
void main() {
  vUv = aUv;
  gl_Position = uMvp * vec4(uMin + aPos * uSize, 1.0);
}`;

// 图集里存的已经是过完显示变换的颜色，直接输出
const FRAG = `#version 300 es
precision mediump float;
uniform sampler2D uTex;
in vec2 vUv;
out vec4 color;
void main() {
  color = vec4(texture(uTex, vUv).rgb, 1.0);
}`;

const GLOW_VERT = `#version 300 es
layout(location = 0) in vec2 aCorner;
uniform vec2 uCenter;
uniform vec2 uHalf;
out vec2 vP;
void main() {
  vP = aCorner;
  gl_Position = vec4(uCenter + aCorner * uHalf, 0.0, 1.0);
}`;

// 与 desk.css 的 .scene-lamp 同一条径向渐变（滤色叠加），所以溶进照片时光晕连续
const GLOW_FRAG = `#version 300 es
precision mediump float;
uniform float uGain;
in vec2 vP;
out vec4 color;
void main() {
  float d = length(vP);
  vec3 c0 = vec3(1.0, 0.808, 0.549) * 0.32;
  vec3 c1 = vec3(0.894, 0.659, 0.408) * 0.13;
  vec3 c = d < 0.4525 ? mix(c0, c1, d / 0.4525) : c1 * clamp(1.0 - (d - 0.4525) / 0.4805, 0.0, 1.0);
  color = vec4(c * uGain, 1.0);
}`;

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** CSS cubic-bezier 的数值解，与 2.5D 推镜用同一条缓动曲线 */
function cubicBezier(x1: number, y1: number, x2: number, y2: number) {
  const cx = 3 * x1;
  const bx = 3 * (x2 - x1) - cx;
  const ax = 1 - cx - bx;
  const cy = 3 * y1;
  const by = 3 * (y2 - y1) - cy;
  const ay = 1 - cy - by;
  return (x: number) => {
    let t = x;
    for (let i = 0; i < 8; i++) {
      const err = ((ax * t + bx) * t + cx) * t - x;
      const slope = (3 * ax * t + 2 * bx) * t + cx;
      if (Math.abs(err) < 1e-5 || Math.abs(slope) < 1e-6) break;
      t -= err / slope;
    }
    return ((ay * t + by) * t + cy) * t;
  };
}

/**
 * 投影 × 视图（列主序）。相机在 pos、对着 target、不带滚转；世界 Z 朝上，不做换轴。
 * b 是视口在单位距离处的视锥边界（偏心投影）。
 */
function viewProjection(out: Float32Array, pos: Vec3, target: Vec3, b: Bounds, near: number, far: number) {
  // 前、右、上
  let fx = target[0] - pos[0];
  let fy = target[1] - pos[1];
  let fz = target[2] - pos[2];
  const fl = Math.hypot(fx, fy, fz);
  fx /= fl;
  fy /= fl;
  fz /= fl;
  const rl = Math.hypot(fx, fy);
  const rx = fy / rl;
  const ry = -fx / rl;
  const ux = ry * fz;
  const uy = -rx * fz;
  const uz = rx * fy - ry * fx;
  // 视图矩阵的三行：右、上、后（相机沿自身 -Z 看）
  const v0 = [rx, ry, 0, -(rx * pos[0] + ry * pos[1])];
  const v1 = [ux, uy, uz, -(ux * pos[0] + uy * pos[1] + uz * pos[2])];
  const v2 = [-fx, -fy, -fz, fx * pos[0] + fy * pos[1] + fz * pos[2]];
  const [l, r, bt, tp] = b;
  const px = 2 / (r - l);
  const pxz = (r + l) / (r - l);
  const py = 2 / (tp - bt);
  const pyz = (tp + bt) / (tp - bt);
  const pz = -(far + near) / (far - near);
  const pzw = (-2 * far * near) / (far - near);
  for (let c = 0; c < 4; c++) {
    out[c * 4] = px * v0[c] + pxz * v2[c];
    out[c * 4 + 1] = py * v1[c] + pyz * v2[c];
    out[c * 4 + 2] = pz * v2[c] + (c === 3 ? pzw : 0);
    out[c * 4 + 3] = -v2[c];
  }
}

/** 视口实际看到的是静帧盒子里的一块：把相机整幅画面的视锥按这块裁出来 */
function viewportBounds(cam: Cam, box: DOMRect, view: DOMRect): Bounds {
  const top = Math.tan(cam.fovY / 2);
  const right = top * cam.aspect;
  const u0 = (view.left - box.left) / box.width;
  const u1 = (view.right - box.left) / box.width;
  const v0 = (view.top - box.top) / box.height;
  const v1 = (view.bottom - box.top) / box.height;
  return [right * (2 * u0 - 1), right * (2 * u1 - 1), top * (1 - 2 * v1), top * (1 - 2 * v0)];
}

function compile(gl: WebGL2RenderingContext, vert: string, frag: string): WebGLProgram {
  const program = gl.createProgram()!;
  for (const [type, src] of [
    [gl.VERTEX_SHADER, vert],
    [gl.FRAGMENT_SHADER, frag],
  ] as const) {
    const shader = gl.createShader(type)!;
    gl.shaderSource(shader, src);
    gl.compileShader(shader);
    gl.attachShader(program, shader);
  }
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program) ?? 'link');
  return program;
}

async function loadBitmap(url: string, signal: AbortSignal): Promise<ImageBitmap> {
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`${res.status}`);
  const blob = await res.blob();
  try {
    return await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
  } catch {
    // 老一些的 Safari 不认第二个参数
    return createImageBitmap(blob);
  }
}

export function startRoom3D() {
  const root = document.documentElement;
  const ctl = window.__intro;
  if (!ctl || !ctl.want3d || !root.classList.contains('intro-hold')) return;

  const canvas = document.querySelector<HTMLCanvasElement>('.intro-canvas');
  const posterBox = document.querySelector<HTMLElement>('.room-intro .scene-cover');
  const heroBox = document.querySelector<HTMLElement>('#hero .scene-cover');
  if (!canvas || !posterBox || !heroBox) return ctl.fail();

  // 时间轴已经不等了（超时或被跳过）就别再下载
  const abort = new AbortController();
  const watch = window.setInterval(() => {
    if (!root.classList.contains('intro-hold')) {
      abort.abort();
      window.clearInterval(watch);
    }
  }, 100);

  // 半尺寸图集：竖屏（手机）一律用——竖幅落点里桌子占的像素少，半尺寸已接近一比一；
  // 横屏只有画布长边不到 1500 像素的小屏才用
  const small =
    window.matchMedia(PORTRAIT).matches ||
    Math.max(window.innerWidth, window.innerHeight) * Math.min(window.devicePixelRatio || 1, 2) < 1500;
  Promise.all([
    fetch(meshUrl, { signal: abort.signal }).then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(`${r.status}`)))),
    loadBitmap(small ? atlas0Half : atlas0, abort.signal),
    loadBitmap(small ? atlas1Half : atlas1, abort.signal),
  ])
    .then(([mesh, ...atlases]) => {
      window.clearInterval(watch);
      if (!root.classList.contains('intro-hold')) return atlases.forEach((a) => a.close());
      run(ctl, root, canvas, posterBox, heroBox, mesh, atlases);
    })
    .catch(() => {
      window.clearInterval(watch);
      ctl.fail();
    });
}

function run(
  ctl: IntroControl,
  root: HTMLElement,
  canvas: HTMLCanvasElement,
  posterBox: HTMLElement,
  heroBox: HTMLElement,
  mesh: ArrayBuffer,
  atlases: ImageBitmap[],
) {
  const gl = canvas.getContext('webgl2', {
    alpha: false,
    antialias: true,
    depth: true,
    stencil: false,
    powerPreference: 'high-performance',
  });
  if (!gl) {
    atlases.forEach((a) => a.close());
    return ctl.fail();
  }

  let raf = 0;
  let disposed = false;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', onResize);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  };
  const onResize = () => {
    if (!disposed) draw(progress);
  };

  let draw: (e: number) => void;
  let progress = 0;

  try {
    // ---- 网格：'MRR1' + JSON 头 + 量化成 uint16 的位置 / UV + 索引 ----
    const headLen = new DataView(mesh).getUint32(4, true);
    const head = JSON.parse(new TextDecoder().decode(new Uint8Array(mesh, 8, headLen))) as {
      min: Vec3;
      size: Vec3;
      groups: { atlas: number; verts: number; indices: number; idx32: boolean; pos: number; uv: number; idx: number }[];
    };
    const base = 8 + headLen;

    const program = compile(gl, VERT, FRAG);
    const uMvp = gl.getUniformLocation(program, 'uMvp');
    gl.useProgram(program);
    gl.uniform3fv(gl.getUniformLocation(program, 'uMin'), head.min);
    gl.uniform3fv(gl.getUniformLocation(program, 'uSize'), head.size);
    gl.uniform1i(gl.getUniformLocation(program, 'uTex'), 0);

    const aniso = gl.getExtension('EXT_texture_filter_anisotropic');
    const groups = head.groups.map((g) => {
      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(gl.ARRAY_BUFFER, new Uint16Array(mesh, base + g.pos, g.verts * 3), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 3, gl.UNSIGNED_SHORT, true, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(gl.ARRAY_BUFFER, new Uint16Array(mesh, base + g.uv, g.verts * 2), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(1);
      gl.vertexAttribPointer(1, 2, gl.UNSIGNED_SHORT, true, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
      gl.bufferData(
        gl.ELEMENT_ARRAY_BUFFER,
        g.idx32 ? new Uint32Array(mesh, base + g.idx, g.indices) : new Uint16Array(mesh, base + g.idx, g.indices),
        gl.STATIC_DRAW,
      );

      const texture = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB8, gl.RGB, gl.UNSIGNED_BYTE, atlases[g.atlas]);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      if (aniso) {
        gl.texParameterf(
          gl.TEXTURE_2D,
          aniso.TEXTURE_MAX_ANISOTROPY_EXT,
          Math.min(8, gl.getParameter(aniso.MAX_TEXTURE_MAX_ANISOTROPY_EXT)),
        );
      }
      return { vao, texture, count: g.indices, type: g.idx32 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT };
    });
    atlases.forEach((a) => a.close());

    // ---- 灯的光晕：屏幕空间的一块方片 ----
    const glow = compile(gl, GLOW_VERT, GLOW_FRAG);
    const uCenter = gl.getUniformLocation(glow, 'uCenter');
    const uHalf = gl.getUniformLocation(glow, 'uHalf');
    const uGain = gl.getUniformLocation(glow, 'uGain');
    const quad = gl.createVertexArray();
    gl.bindVertexArray(quad);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);

    // ---- 镜头：横屏、竖屏各一对机位 ----
    const cams: Record<string, Cam> = scene.cams;
    const [startName, endName] = scene.pairs[window.matchMedia(PORTRAIT).matches ? 'p' : 'l'];
    const camA = cams[startName];
    const camB = cams[endName];
    const ctrl = scene.ctrl as Vec3;
    const bulb = scene.bulb as Vec3;
    const mvp = new Float32Array(16);
    const born = performance.now();

    draw = (e: number) => {
      const view = canvas.getBoundingClientRect();
      // 画布像素封顶在约 420 万（镜头在动、落定后又溶进照片，更高的分辨率看不出来）
      const dpr = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(4.2e6 / Math.max(1, view.width * view.height)));
      const w = Math.max(1, Math.round(view.width * dpr));
      const h = Math.max(1, Math.round(view.height * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      // 取景：起点对齐进门静帧的盒子，终点对齐 Hero 照片的盒子
      const boxA = posterBox.getBoundingClientRect();
      const boxB = heroBox.getBoundingClientRect();
      const bA = viewportBounds(camA, boxA, view);
      const bB = viewportBounds(camB, boxB, view);
      const bounds = bA.map((v, i) => lerp(v, bB[i], e)) as Bounds;
      // 位置走二次贝塞尔（先直着穿过门洞，再拐向书桌），一路盯着信附近的一点
      const k = (1 - e) * (1 - e);
      const m = 2 * e * (1 - e);
      const pos = [0, 1, 2].map((i) => k * camA.pos[i] + m * ctrl[i] + e * e * camB.pos[i]) as Vec3;
      const target = [0, 1, 2].map((i) => lerp(camA.look[i], camB.look[i], e)) as Vec3;
      viewProjection(mvp, pos, target, bounds, scene.near, scene.far);

      gl.viewport(0, 0, w, h);
      gl.clearColor(0.043, 0.039, 0.035, 1);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.BLEND);
      gl.useProgram(program);
      gl.uniformMatrix4fv(uMvp, false, mvp);
      gl.activeTexture(gl.TEXTURE0);
      for (const g of groups) {
        gl.bindVertexArray(g.vao);
        gl.bindTexture(gl.TEXTURE_2D, g.texture);
        gl.drawElements(gl.TRIANGLES, g.count, g.type, 0);
      }

      // 光晕：跟着灯泡在画面里的位置走，大小随静帧盒子（与 .scene-lamp 的 30% 一致），带同样的呼吸
      const cw = mvp[3] * bulb[0] + mvp[7] * bulb[1] + mvp[11] * bulb[2] + mvp[15];
      if (cw > 0) {
        const cx = (mvp[0] * bulb[0] + mvp[4] * bulb[1] + mvp[8] * bulb[2] + mvp[12]) / cw;
        const cy = (mvp[1] * bulb[0] + mvp[5] * bulb[1] + mvp[9] * bulb[2] + mvp[13]) / cw;
        const breath = 0.5 - 0.5 * Math.cos(((performance.now() - born) / 3400) * Math.PI * 2);
        const size = 0.3 * lerp(boxA.width, boxB.width, e) * (1 + 0.06 * breath);
        gl.disable(gl.DEPTH_TEST);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE_MINUS_DST_COLOR, gl.ONE);
        gl.useProgram(glow);
        gl.uniform2f(uCenter, cx, cy);
        gl.uniform2f(uHalf, size / view.width, size / view.height);
        gl.uniform1f(uGain, 0.8 + 0.2 * breath);
        gl.bindVertexArray(quad);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      }
      gl.bindVertexArray(null);
    };

    canvas.addEventListener('webglcontextlost', () => {
      canvas.style.opacity = '0';
      dispose();
    });
    draw(0);
    if (gl.getError() !== gl.NO_ERROR) throw new Error('gl');
  } catch {
    atlases.forEach((a) => a.close());
    dispose();
    return ctl.fail();
  }

  // 第一帧已经画好；交给时间轴，由它决定什么时候开拍（或者已经来不及了）
  const ease = cubicBezier(0.42, 0.04, 0.2, 1);
  let manual = false;
  if (import.meta.env.DEV) {
    // 调镜头用（仅开发构建）：控制台里 __room3d.scrub(0.5) 把镜头停在任意进度
    (window as unknown as Record<string, unknown>).__room3d = {
      scrub(e: number) {
        manual = true;
        progress = e;
        draw(e);
      },
    };
  }
  const started = ctl.ready(() => {
    const t0 = performance.now();
    const tick = (now: number) => {
      if (disposed || manual) return;
      if (root.classList.contains('intro-done')) return dispose();
      progress = ease(clamp01((now - t0) / (ctl.T.move * 1000)));
      draw(progress);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  });
  if (!started) return dispose();
  window.addEventListener('resize', onResize);
}
