/**
 * 仅开发服务器用：给房间静帧的地址补上文件的修改时间。
 *
 * 开发服务器的 /_image 响应带一年的缓存头，地址里却没有内容哈希——重渲染（npm run room）之后
 * 文件名没变，浏览器就一直拿旧图，看上去像「新房间配旧照片」。
 * 正式构建的文件名自带内容哈希，不需要这一步：非开发环境下原样返回。
 */
import { statSync } from 'node:fs';
import type { ImageMetadata } from 'astro';

/** 返回一个函数：把字符串（单个地址或 srcset）里的 /_image 地址都带上这张图的修改时间 */
export function fresh(image: ImageMetadata): (urls: string) => string {
  if (!import.meta.env.DEV) return (urls) => urls;
  try {
    const { fsPath } = image as ImageMetadata & { fsPath?: string };
    const stamp = Math.round(statSync(fsPath ?? '').mtimeMs);
    return (urls) => urls.replace(/\/_image\?[^\s,]+/g, (url) => `${url}&v=${stamp}`);
  } catch {
    return (urls) => urls;
  }
}
