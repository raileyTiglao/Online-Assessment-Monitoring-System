// src/components/animations/ThemeToggleStarfield.tsx — small persistent
// Three.js starfield inside the sidebar's theme-toggle pill. Ported from
// php_backend/assets/theme-toggle-stars.js. Global (rendered once in
// Sidebar, present on every authenticated page) — unlike HeroStarfield,
// this does not mount/unmount per route, but still disposes fully if the
// user ever signs out (Sidebar unmounts with the rest of AppLayout).

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useTheme } from "../../theme/ThemeContext";
import { createTwinklingStars, disposeTwinklingField, type TwinklingField } from "./starfieldShared";

const STAR_COUNT = 20;

// Matches --color-on-hero per theme (#efe9db dark / #16232e light).
const DARK_COLOR = new THREE.Color(0.937, 0.914, 0.859);
const LIGHT_COLOR = new THREE.Color(0.086, 0.137, 0.18);

function currentColor(theme: string) {
  return theme === "light" ? LIGHT_COLOR : DARK_COLOR;
}

export function ThemeToggleStarfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();
  const fieldRef = useRef<TwinklingField | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const width = canvas.clientWidth || 140;
    const height = canvas.clientHeight || 40;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height, false);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(0, width, height, 0, -10, 10);

    const field = createTwinklingStars(
      STAR_COUNT,
      width,
      height,
      currentColor(theme),
      [1, 2.8],
      { speed: 2.2, floor: 0.4, gain: 0.6, alphaCap: 1.0 },
    );
    scene.add(field.points);
    fieldRef.current = field;

    let rafId = 0;

    if (reducedMotion) {
      // Render exactly one static frame, no animation loop — intentionally
      // different from HeroStarfield, which fully skips setup instead.
      renderer.render(scene, camera);
    } else {
      const tick = (now: number) => {
        rafId = requestAnimationFrame(tick);
        field.material.uniforms.uTime.value = now / 1000;
        renderer.render(scene, camera);
      };
      rafId = requestAnimationFrame(tick);
    }

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      disposeTwinklingField(field);
      renderer.dispose();
      fieldRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const field = fieldRef.current;
    if (!field) return;
    field.material.uniforms.uColor.value = currentColor(theme);
  }, [theme]);

  return <canvas className="theme-pill__canvas" ref={canvasRef} />;
}
