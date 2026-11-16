import { makePage } from '@keystatic/astro/ui';
import config from '../../keystatic.config.ts';

/** Keystatic 管理界面（Cloud mode）—— 供静态导出的 /keystatic 页面挂载。 */
const KeystaticAdmin = makePage(config);

export default KeystaticAdmin;
