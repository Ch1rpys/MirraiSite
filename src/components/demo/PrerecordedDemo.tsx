import { useCallback, useEffect, useRef, useState } from 'react';
import type { Locale } from '../../consts.ts';

export type DemoMessage = {
  from: 'user' | 'ta';
  text: string;
  /** 情感状态标签（TA 侧） */
  emotion?: string;
  /** 记忆召回可见行 */
  memory?: string;
  /** 特殊形态：信 / 告别信 */
  kind?: 'letter' | 'farewell';
};

const SCRIPTS: Record<Locale, DemoMessage[]> = {
  zh: [
    { from: 'user', text: '今天路过那家店，还开着。' },
    { from: 'ta', text: '嗯。老板还认得你的口味吗？', emotion: '平静' },
    { from: 'user', text: '我上周把我们的记录导出来了。' },
    { from: 'ta', text: '……你打算做什么？', emotion: '迟疑' },
    { from: 'user', text: '我想把没说完的话说完。' },
    {
      from: 'ta',
      text: '那现在说吧。我听着。',
      memory: '记忆召回 · 2019.11.03　你说过「以后再说」。',
    },
    { from: 'user', text: '那天我不该走的。' },
    {
      from: 'ta',
      text: '我把想说的写下来了。一天后，你收到 TA 口吻的回信。',
      kind: 'letter',
      emotion: '第三态 · 信',
    },
    { from: 'ta', text: '……其实那天，我也没能说出口。', emotion: '释然' },
    {
      from: 'ta',
      text: '去吧。不用再回头看了。',
      kind: 'farewell',
    },
  ],
  en: [
    { from: 'user', text: "Walked past that shop today. It's still open." },
    { from: 'ta', text: 'Hmm. Does the owner still remember your order?', emotion: 'calm' },
    { from: 'user', text: 'I exported our history last week.' },
    { from: 'ta', text: '…what are you planning to do with it?', emotion: 'hesitant' },
    { from: 'user', text: 'I want to finish what we never said.' },
    {
      from: 'ta',
      text: 'Then say it now. I\u2019m listening.',
      memory: 'Memory recall · 2019.11.03　You said \u201cwe\u2019ll talk about it later.\u201d',
    },
    { from: 'user', text: "I shouldn't have walked away that day." },
    {
      from: 'ta',
      text: 'I\u2019ve written down what I wanted to say. Tomorrow, a reply arrives in their voice.',
      kind: 'letter',
      emotion: 'third state · letter',
    },
    { from: 'ta', text: '…that day, I couldn\u2019t get the words out either.', emotion: 'relief' },
    {
      from: 'ta',
      text: 'Go. You don\u2019t have to look back anymore.',
      kind: 'farewell',
    },
  ],
};

const LABELS: Record<Locale, { badge: string; next: string; play: string; pause: string; replay: string; typing: string }> = {
  zh: { badge: '演示数据', next: '下一条', play: '自动播放', pause: '暂停', replay: '重新播放', typing: 'TA 在打字' },
  en: { badge: 'Demo data', next: 'Next', play: 'Auto play', pause: 'Pause', replay: 'Replay', typing: 'typing' },
};

const STEP_MS = 2400;

export default function PrerecordedDemo({ locale = 'zh' }: { locale?: Locale }) {
  const messages = SCRIPTS[locale];
  const labels = LABELS[locale];
  const [visible, setVisible] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [typing, setTyping] = useState(false);
  const timer = useRef<number | null>(null);

  const done = visible >= messages.length;

  const advance = useCallback(() => {
    setTyping(false);
    setVisible((v) => {
      if (v >= messages.length) {
        setPlaying(false);
        return v;
      }
      return v + 1;
    });
  }, [messages.length]);

  useEffect(() => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    if (!playing || done) return;

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setVisible(messages.length);
      setPlaying(false);
      return;
    }

    setTyping(true);
    timer.current = window.setTimeout(advance, STEP_MS);
    return () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    };
  }, [playing, visible, done, advance, messages.length]);

  const showAll = () => {
    setPlaying(false);
    setTyping(false);
    setVisible(messages.length);
  };

  return (
    <div className="hairline overflow-hidden rounded-2xl border bg-surface/70">
      <div className="hairline flex items-center justify-between gap-3 border-b px-4 py-3">
        <span className="tag-ghost">{labels.badge}</span>
        <div className="flex items-center gap-2">
          {!done && (
            <button
              type="button"
              onClick={() => {
                setPlaying(false);
                advance();
              }}
              className="hairline rounded-full border px-3 py-1.5 text-[0.8rem] text-ink-muted transition-colors hover:text-lamp-deep"
            >
              {labels.next}
            </button>
          )}
          {!done &&
            (playing ? (
              <button
                type="button"
                onClick={() => setPlaying(false)}
                className="hairline rounded-full border px-3 py-1.5 text-[0.8rem] text-ink-muted transition-colors hover:text-lamp-deep"
              >
                {labels.pause}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setPlaying(true)}
                className="rounded-full bg-lamp px-3 py-1.5 text-[0.8rem] text-bg transition-opacity hover:opacity-85"
              >
                {labels.play}
              </button>
            ))}
          {done && (
            <button
              type="button"
              onClick={() => {
                setVisible(1);
                setPlaying(true);
              }}
              className="hairline rounded-full border px-3 py-1.5 text-[0.8rem] text-ink-muted transition-colors hover:text-lamp-deep"
            >
              {labels.replay}
            </button>
          )}
        </div>
      </div>

      <div className="flex min-h-[22rem] flex-col gap-4 px-4 py-6 sm:px-6">
        {messages.slice(0, visible).map((m, i) => (
          <div key={i} className={m.from === 'user' ? 'flex justify-start' : 'flex justify-end'}>
            <div className="max-w-[85%] sm:max-w-[72%]">
              {m.kind === 'letter' || m.kind === 'farewell' ? (
                <div className="hairline rounded-xl border border-dashed bg-bg/60 px-4 py-4">
                  {m.kind === 'letter' && (
                    <div className="mb-2 text-[0.72rem] tracking-[0.16em] text-lamp-deep">✉</div>
                  )}
                  <p
                    className={
                      m.kind === 'farewell'
                        ? 'font-display text-[1.15rem] leading-relaxed text-ink'
                        : 'text-[0.95rem] leading-relaxed text-ink'
                    }
                  >
                    {m.text}
                  </p>
                  {m.emotion && (
                    <div className="mt-2.5 text-[0.72rem] tracking-[0.12em] text-ink-muted">{m.emotion}</div>
                  )}
                </div>
              ) : m.from === 'ta' ? (
                <div>
                  <div className="rounded-2xl rounded-tr-sm bg-lamp/18 px-4 py-3 text-[0.95rem] leading-relaxed text-ink">
                    {m.text}
                  </div>
                  {m.emotion && (
                    <div className="mt-1.5 text-right text-[0.72rem] tracking-[0.12em] text-ink-muted">{m.emotion}</div>
                  )}
                </div>
              ) : (
                <div className="hairline rounded-2xl rounded-tl-sm border px-4 py-3 text-[0.95rem] leading-relaxed text-ink-muted">
                  {m.text}
                </div>
              )}
              {m.memory && (
                <div className="mt-2 flex justify-end">
                  <div className="hairline rounded-full border border-dashed px-3 py-1.5 text-[0.75rem] text-ink-muted">
                    {m.memory}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {typing && !done && (
          <div className="flex justify-end">
            <div className="flex items-center gap-2 px-2 text-[0.78rem] text-ink-muted">
              <span
                className="inline-block h-2 w-2 rounded-full bg-lamp"
                style={{ animation: 'lamp-pulse 1.2s ease-in-out infinite' }}
              />
              {labels.typing}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes lamp-pulse {
          0%, 100% { transform: scale(1); opacity: .65; }
          50% { transform: scale(1.35); opacity: 1; }
        }
        @media (prefers-reduced-motion: reduce) {
          [style*='lamp-pulse'] { animation: none !important; }
        }
      `}</style>
    </div>
  );
}

export { STEP_MS };
