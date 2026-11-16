/** 站点级常量：链接、仓库、邮箱。M1 期下载 CTA 直指 GitHub Releases（M2.6 切回 /download）。 */

export const SITE = {
  domain: 'mirrai.ink',
  url: 'https://mirrai.ink',
  name: 'Mirrai',
  email: 'ch1rpy@163.com',
} as const;

export const REPO = {
  url: 'https://github.com/Ch1rpys/Mirrai',
  releases: 'https://github.com/Ch1rpys/Mirrai/releases',
  discussions: 'https://github.com/Ch1rpys/Mirrai/discussions',
  issues: 'https://github.com/Ch1rpys/Mirrai/issues',
  // 产品仓库 Releases API（scripts/fetch-releases.mjs）
  releasesApi: 'https://api.github.com/repos/Ch1rpys/Mirrai/releases',
} as const;

/** 站点仓库（官网本身） */
export const SITE_REPO = {
  url: 'https://github.com/Ch1rpys/MirraiSite',
} as const;

export type Locale = 'zh' | 'en';

export const LOCALES: Locale[] = ['zh', 'en'];

export function localeFromUrl(url: URL): Locale {
  return url.pathname.startsWith('/en') ? 'en' : 'zh';
}

export function localizedPath(path: string, locale: Locale): string {
  const clean = path === '/' ? '' : path;
  return locale === 'en' ? `/en${clean}` : clean || '/';
}

/** hreflang 互标（M1.5） */
export function alternateLinks(path: string) {
  const clean = path.replace(/^\/en(?=\/|$)/, '') || '/';
  return {
    zh: clean,
    en: clean === '/' ? '/en/' : `/en${clean}`,
  };
}

/**
 * M1 期降级链接策略（零死链）：主 CTA 直指 GitHub Releases。
 * M2.6 已切换：Hero/S8 走 /download。
 */
export const USE_GITHUB_RELEASES_CTA = false;

export const GITHUB_RELEASES = REPO.releases;

/**
 * `/go/*` 跳转链目标（零脚本转化统计，只量安装包与 Docker）。
 * Docker 镜像发布前暂指 Releases 页；镜像发布后改为 Docker Hub 镜像页。
 */
export const GO_LINKS = {
  macos: 'https://github.com/Ch1rpys/Mirrai/releases/latest/download/Mirrai-macOS-arm64.dmg',
  windows: 'https://github.com/Ch1rpys/Mirrai/releases/latest/download/Mirrai-Setup-x64.exe',
  docker: REPO.releases,
} as const;

export type GoSlug = keyof typeof GO_LINKS;
