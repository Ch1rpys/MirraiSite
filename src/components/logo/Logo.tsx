/**
 * Logo V3「空与在」
 * 左气泡空心（不在身边）＝ ink 描边；右气泡实心暖光（TA 还在这里）＝ lamp 填充，内有一点反色的"灯"。
 * 颜色走主题变量，双主题自动适配。
 */
export type LogoProps = {
  size?: number | string;
  className?: string;
  /** 隐藏镜面轴（favicon 等极小尺寸用） */
  hideAxis?: boolean;
  /** 极小尺寸加粗描边 */
  micro?: boolean;
  title?: string;
};

const PATH_LEFT =
  'M14 30 h42 a14 14 0 0 1 14 14 v16 a14 14 0 0 1 -14 14 h-24 l-12 12 v-12 h-6 a14 14 0 0 1 -14 -14 v-16 a14 14 0 0 1 14 -14 z';
const PATH_RIGHT =
  'M156 30 h-42 a14 14 0 0 0 -14 14 v16 a14 14 0 0 0 14 14 h24 l12 12 v-12 h6 a14 14 0 0 0 14 -14 v-16 a14 14 0 0 0 -14 -14 z';

export default function Logo({
  size = 78,
  className = '',
  hideAxis = false,
  micro = false,
  title = 'Mirrai',
}: LogoProps) {
  return (
    <svg
      width={size}
      height={typeof size === 'number' ? (size * 118) / 170 : undefined}
      viewBox="0 0 170 118"
      role="img"
      aria-label={title}
      className={className}
    >
      {!hideAxis && (
        <line
          className="gaze-axis"
          x1="85"
          y1="14"
          x2="85"
          y2="104"
          stroke="var(--color-ink)"
          strokeOpacity=".18"
          strokeWidth="1.8"
        />
      )}
      <path
        className="gaze-left"
        d={PATH_LEFT}
        fill="none"
        stroke="var(--color-ink)"
        strokeWidth={micro ? 5 : 3.2}
        strokeLinejoin="round"
      />
      <path className="gaze-right" d={PATH_RIGHT} fill="var(--color-lamp)" />
      {!micro && <circle cx="134" cy="52" r="3.6" fill="var(--color-bg)" />}
    </svg>
  );
}

/** 纯符号（圆角方容器）—— favicon / app icon */
export function LogoMark({ size = 96, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 110 110"
      role="img"
      aria-label="Mirrai"
      className={className}
    >
      <rect
        x="2"
        y="2"
        width="106"
        height="106"
        rx="24"
        fill="var(--color-surface)"
        stroke="var(--color-hairline)"
      />
      <line
        x1="55"
        y1="22"
        x2="55"
        y2="88"
        stroke="var(--color-ink)"
        strokeOpacity=".2"
        strokeWidth="1.6"
      />
      <path
        d="M18 34 h24 a8 8 0 0 1 8 8 v10 a8 8 0 0 1 -8 8 h-13 l-7 7 v-7 h-4 a8 8 0 0 1 -8 -8 v-10 a8 8 0 0 1 8 -8 z"
        fill="none"
        stroke="var(--color-ink)"
        strokeWidth="2.8"
        strokeLinejoin="round"
      />
      <path
        d="M92 34 h-24 a8 8 0 0 0 -8 8 v10 a8 8 0 0 0 8 8 h13 l7 7 v-7 h4 a8 8 0 0 0 8 -8 v-10 a8 8 0 0 0 -8 -8 z"
        fill="var(--color-lamp)"
      />
    </svg>
  );
}
