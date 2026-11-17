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

const LABELS: Record<
  Locale,
  { badge: string; next: string; play: string; pause: string; replay: string; typing: string; me: string; ta: string }
> = {
  zh: { badge: '演示数据', next: '下一条', play: '自动播放', pause: '暂停', replay: '重新播放', typing: 'TA 在打字', me: '我', ta: 'TA' },
  en: { badge: 'Demo data', next: 'Next', play: 'Auto play', pause: 'Pause', replay: 'Replay', typing: 'typing', me: 'you', ta: 'them' },
};

const STEP_MS = 2400;

/** 预录对话回放：写在一页撕下来的横线本上，控件就在纸的下沿。 */
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

  return (
    <div className="paper-lift demo-wrap">
      <div className="paper paper-white paper-lined paper-torn demo-page">
        <span className="demo-badge">{labels.badge}</span>

        <ol className="demo-lines" aria-live="polite">
          {messages.slice(0, visible).map((m, i) => (
            <li key={i} className={`demo-line demo-${m.from}${m.kind === 'farewell' ? ' demo-is-farewell' : ''}`}>
              <span className="demo-who" aria-hidden="true">
                {m.from === 'user' ? labels.me : labels.ta}
              </span>
              <div className="demo-text">
                {m.kind === 'letter' ? (
                  <div className="paper demo-letter">
                    <span className="demo-letter-mark" aria-hidden="true">
                      ✉
                    </span>
                    {m.text}
                  </div>
                ) : (
                  <p className={m.kind === 'farewell' ? 'demo-farewell' : undefined}>{m.text}</p>
                )}
                {m.emotion && <span className="demo-emotion">· {m.emotion}</span>}
                {m.memory && <span className="demo-memory">↳ {m.memory}</span>}
              </div>
            </li>
          ))}
          {typing && !done && (
            <li className="demo-line demo-typing">
              <span className="demo-who" aria-hidden="true" />
              <span className="demo-typing-text">
                <span className="demo-lamp" aria-hidden="true" />
                {labels.typing}
              </span>
            </li>
          )}
        </ol>

        <div className="demo-controls">
          {!done && (
            <button
              type="button"
              onClick={() => {
                setPlaying(false);
                advance();
              }}
            >
              {labels.next}
            </button>
          )}
          {!done &&
            (playing ? (
              <button type="button" onClick={() => setPlaying(false)}>
                {labels.pause}
              </button>
            ) : (
              <button type="button" className="is-primary" onClick={() => setPlaying(true)}>
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
            >
              {labels.replay}
            </button>
          )}
        </div>
      </div>

      <style>{`
        .demo-wrap { rotate: 0.6deg; }
        .demo-page {
          --margin-x: 3.4rem;
          --lines-top: 3.9rem;
          padding: 3.9rem 1.6rem 1.4rem 0;
          min-height: 36rem;
          display: flex;
          flex-direction: column;
        }
        .demo-badge {
          position: absolute;
          top: 1.35rem;
          right: 1.4rem;
          padding: 0.1rem 0.6rem;
          border: 1.5px solid rgba(168, 70, 56, 0.55);
          border-radius: 3px;
          rotate: -3deg;
          font-size: 0.68rem;
          line-height: 1.6;
          letter-spacing: 0.2em;
          color: rgba(168, 70, 56, 0.8);
        }
        .demo-lines { flex: 1; }
        .demo-line {
          display: grid;
          grid-template-columns: var(--margin-x) 1fr;
          animation: demo-ink 0.7s ease-out both;
        }
        .demo-who {
          padding-right: 0.7rem;
          text-align: right;
          font-size: 0.7rem;
          letter-spacing: 0.08em;
          color: var(--paper-pencil);
        }
        .demo-text { padding-left: 0.9rem; }
        .demo-user .demo-text p { color: var(--paper-ink-muted); font-size: 0.97rem; }
        .demo-ta .demo-text p {
          color: var(--paper-ink);
          font-family: var(--font-display);
          font-size: 1.06rem;
        }
        .demo-emotion, .demo-memory {
          display: block;
          font-size: 0.75rem;
          letter-spacing: 0.06em;
          color: var(--paper-pencil);
        }
        .demo-memory {
          width: fit-content;
          text-decoration: underline dashed rgba(122, 109, 93, 0.6);
          text-underline-offset: 0.3em;
        }
        .demo-letter {
          margin: 0.5rem 0;
          padding: 0.45rem 1rem 0.55rem;
          rotate: -1deg;
          width: fit-content;
          max-width: 100%;
          font-size: 0.95rem;
          line-height: 1.75rem;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18), 0 6px 12px -6px rgba(0, 0, 0, 0.3);
        }
        .demo-letter-mark { margin-right: 0.5rem; color: #a26a37; }
        .demo-is-farewell { margin-top: 1.95rem; align-items: baseline; }
        .demo-text p.demo-farewell {
          font-size: 1.4rem;
          color: #8f5a2e;
        }
        .demo-typing-text {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding-left: 0.9rem;
          font-size: 0.78rem;
          color: var(--paper-pencil);
        }
        .demo-lamp {
          width: 0.5rem;
          height: 0.5rem;
          border-radius: 50%;
          background: #e4a868;
          box-shadow: 0 0 10px rgba(228, 168, 104, 0.8);
          animation: demo-lamp 1.2s ease-in-out infinite;
        }
        .demo-controls {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem 1.4rem;
          margin-top: 1.95rem;
          padding-left: calc(var(--margin-x) + 0.9rem);
        }
        .demo-controls button {
          font-size: 0.82rem;
          letter-spacing: 0.08em;
          color: var(--paper-ink-muted);
          text-decoration: underline;
          text-decoration-color: rgba(42, 35, 28, 0.25);
          text-underline-offset: 0.3em;
          transition: color 0.2s;
        }
        .demo-controls button:hover { color: #8f5a2e; }
        .demo-controls button.is-primary { color: #8f5a2e; text-decoration-color: rgba(143, 90, 46, 0.5); }
        @keyframes demo-ink { from { opacity: 0; filter: blur(1.5px); } to { opacity: 1; filter: none; } }
        @keyframes demo-lamp {
          0%, 100% { transform: scale(1); opacity: .65; }
          50% { transform: scale(1.35); opacity: 1; }
        }
        @media (max-width: 639px) {
          .demo-page { --margin-x: 2.6rem; padding-right: 1.1rem; }
        }
        @media (prefers-reduced-motion: reduce) {
          .demo-line, .demo-lamp { animation: none; }
        }
      `}</style>
    </div>
  );
}

export { STEP_MS };
