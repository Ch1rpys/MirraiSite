import Logo, { LogoMark } from './Logo.tsx';
import Wordmark from './Wordmark.tsx';

/**
 * Lockup 四形态：
 *  horizontal — 桌面导航 / Hero
 *  vertical   — 移动端 / 分享卡
 *  mark       — favicon / app icon
 *  wordmark   — 页脚 / 版权行
 */
export type LockupProps = {
  variant?: 'horizontal' | 'vertical' | 'mark' | 'wordmark';
  /** 符号宽度（px） */
  symbolSize?: number;
  /** 字标字号（px） */
  wordmarkSize?: number;
  className?: string;
  title?: string;
};

export default function Lockup({
  variant = 'horizontal',
  symbolSize = 78,
  wordmarkSize = 30,
  className = '',
  title = 'Mirrai',
}: LockupProps) {
  if (variant === 'mark') {
    return <LogoMark size={symbolSize} className={className} />;
  }
  if (variant === 'wordmark') {
    return <Wordmark size={wordmarkSize} className={className} />;
  }
  if (variant === 'vertical') {
    return (
      <span className={`flex flex-col items-center gap-3 ${className}`}>
        <Logo size={symbolSize} title={title} />
        <Wordmark size={wordmarkSize} />
      </span>
    );
  }
  return (
    <span className={`flex items-center gap-4 ${className}`}>
      <Logo size={symbolSize} title={title} />
      <Wordmark size={wordmarkSize} />
    </span>
  );
}
