/**
 * 字标：Cormorant Garamond，字距 .22em（text-indent 抵消右侧字距）
 */
export type WordmarkProps = {
  size?: number | string;
  className?: string;
};

export default function Wordmark({ size = 30, className = '' }: WordmarkProps) {
  return (
    <span
      className={`font-wordmark leading-none ${className}`}
      style={{
        fontSize: size,
        letterSpacing: '.22em',
        textIndent: '.22em',
        fontWeight: 500,
      }}
    >
      Mirrai
    </span>
  );
}
