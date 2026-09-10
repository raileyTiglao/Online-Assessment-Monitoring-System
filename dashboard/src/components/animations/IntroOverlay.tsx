// src/components/animations/IntroOverlay.tsx — one-time full-screen star
// shower splash, ported from php_backend/assets/intro.js. Pure CSS-keyframe
// DOM particles, no canvas/Three.js. Shows once per browser tab session
// (sessionStorage-gated) unless prefers-reduced-motion is set.
//
// The show/skip decision AND the sessionStorage flag write happen in the
// useState lazy initializer, NOT in a useEffect — under StrictMode's dev
// double-invoke, an effect-based check-and-set would see effect #1 write
// the flag, then effect #2 (after the throwaway cleanup) read that same
// flag and believe it already ran, silently never showing the overlay.
// A lazy initializer runs exactly once for the real first render and is
// immune to that.

import { useEffect, useState, type CSSProperties } from "react";

// CSS custom properties aren't part of React's CSSProperties type — this
// cast is the standard escape hatch for setting them via inline style.
type StyleWithVars = CSSProperties & Record<`--${string}`, string | number>;

const STAR_COUNT = 18;
const DOT_COUNT = 90;
const SHOWER_DURATION_MS = 2600;
const SESSION_KEY = "oams-intro-shown";

function rand(min: number, max: number) {
  return min + Math.random() * (max - min);
}

interface DotSpec {
  key: number;
  left: number;
  top: number;
  size: number;
  peak: number;
  duration: number;
  delay: number;
}

interface StarSpec {
  key: number;
  gradId: string;
  left: number;
  top: number;
  size: number;
  tailWidth: number;
  tailHeight: number;
  travelX: number;
  travelY: number;
  duration: number;
  delay: number;
}

function buildDots(): DotSpec[] {
  return Array.from({ length: DOT_COUNT }, (_, i) => {
    const depth = Math.random();
    return {
      key: i,
      left: rand(0, 100),
      top: rand(0, 100),
      size: rand(1.2, 3.4) * (0.6 + depth * 0.4),
      peak: rand(0.35, 1),
      duration: rand(1.4, 3.2),
      delay: rand(0, 2.4),
    };
  });
}

function buildStars(): StarSpec[] {
  return Array.from({ length: STAR_COUNT }, (_, i) => {
    const depth = Math.random();
    const size = 14 + depth * 60;
    const tailWidth = size * rand(3.2, 4.8);
    const distance = rand(70, 110);
    return {
      key: i,
      gradId: `introTailGrad${i}`,
      left: rand(30, 135),
      top: rand(-20, 55),
      size,
      tailWidth,
      tailHeight: tailWidth * 0.26,
      travelX: -distance,
      travelY: distance,
      duration: rand(1.1, 1.9),
      delay: rand(0, 1.2),
    };
  });
}

function decideShouldShow(): boolean {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
  try {
    if (sessionStorage.getItem(SESSION_KEY) === "1") return false;
    sessionStorage.setItem(SESSION_KEY, "1");
  } catch {
    // sessionStorage unavailable — fall through and show once, no persistence possible
  }
  return true;
}

export function IntroOverlay() {
  const [show] = useState(decideShouldShow);
  const [particles] = useState(() => (show ? { dots: buildDots(), stars: buildStars() } : null));
  const [hidden, setHidden] = useState(false);
  const [unmounted, setUnmounted] = useState(!show);

  useEffect(() => {
    if (!show) return;
    const timer = setTimeout(() => setHidden(true), SHOWER_DURATION_MS);
    return () => clearTimeout(timer);
  }, [show]);

  if (unmounted || !particles) return null;

  return (
    <div
      className={hidden ? "intro-overlay is-hidden" : "intro-overlay"}
      style={{ pointerEvents: "none" }}
      onTransitionEnd={() => setUnmounted(true)}
    >
      <div className="intro-field" style={{ pointerEvents: "none" }}>
        {particles.dots.map((d) => (
          <span
            key={d.key}
            className="intro-dot"
            style={{
              left: `${d.left}vw`,
              top: `${d.top}vh`,
              "--dot-size": `${d.size}px`,
              "--dot-peak": d.peak,
              "--twinkle-duration": `${d.duration}s`,
              "--twinkle-delay": `${d.delay}s`,
            } as StyleWithVars}
          />
        ))}
        {particles.stars.map((s) => (
          <div
            key={s.key}
            className="intro-star"
            style={{
              left: `${s.left}vw`,
              top: `${s.top}vh`,
              "--travel-x": `${s.travelX}vw`,
              "--travel-y": `${s.travelY}vh`,
              "--travel-duration": `${s.duration}s`,
              "--travel-delay": `${s.delay}s`,
            } as StyleWithVars}
          >
            <svg
              className="intro-star-tail"
              width={s.tailWidth}
              height={s.tailHeight}
              viewBox={`0 0 ${s.tailWidth} ${s.tailHeight}`}
            >
              <defs>
                <linearGradient id={s.gradId} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
                  <stop offset="100%" stopColor="#ffffff" stopOpacity="0.9" />
                </linearGradient>
              </defs>
              <ellipse
                cx={s.tailWidth / 2}
                cy={s.tailHeight / 2}
                rx={s.tailWidth / 2}
                ry={s.tailHeight / 2}
                fill={`url(#${s.gradId})`}
              />
            </svg>
            <svg className="intro-star-core" width={s.size} height={s.size} viewBox="0 0 24 24">
              <path
                d="M12 0 L14.5 9.5 L24 12 L14.5 14.5 L12 24 L9.5 14.5 L0 12 L9.5 9.5 Z"
                fill="#ffffff"
              />
            </svg>
          </div>
        ))}
      </div>
    </div>
  );
}
