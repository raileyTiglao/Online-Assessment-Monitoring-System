// src/components/animations/HeroStarfield.tsx — persistent Three.js
// starfield inside the dashboard hero. Ported from
// php_backend/assets/hero-stars.js. Unlike the PHP version (one page-load
// lifetime), this mounts/unmounts on every visit to "/" via react-router,
// so full WebGL disposal on unmount is required — see the plan's Risk #1.

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useTheme } from "../../theme/ThemeContext";
import { createTwinklingStars, disposeTwinklingField, type TwinklingField } from "./starfieldShared";

const STAR_COUNT = 90;
const SHOOTING_STAR_COUNT = 3;

const DARK_COLOR = new THREE.Color(1, 1, 1);
const LIGHT_COLOR = new THREE.Color(0.09, 0.16, 0.24);

const SHOOTING_VERTEX = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const SHOOTING_FRAGMENT = `
  uniform float uOpacity;
  uniform vec3 uColor;
  varying vec2 vUv;
  void main() {
    float head = smoothstep(0.0, 1.0, vUv.x);
    gl_FragColor = vec4(uColor, head * uOpacity);
  }
`;

interface ShootingStar {
  mesh: THREE.Mesh;
  material: THREE.ShaderMaterial;
  active: boolean;
  startX: number;
  startY: number;
  angle: number;
  travel: number;
  duration: number;
  startTime: number;
  nextSpawn: number;
}

function currentColor(theme: string) {
  return theme === "light" ? LIGHT_COLOR : DARK_COLOR;
}

export function HeroStarfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();
  const sceneRef = useRef<{
    field: TwinklingField;
    shootingStars: ShootingStar[];
  } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const hero = canvas?.parentElement;
    if (!canvas || !hero) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return; // fully skip setup, matches hero-stars.js's reduced-motion behavior
    }

    let width = hero.clientWidth;
    let height = hero.clientHeight;

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
      [1, 3],
      { speed: 2.0, floor: 0.35, gain: 0.65, alphaCap: 0.85 },
    );
    scene.add(field.points);

    const shootingStars: ShootingStar[] = Array.from({ length: SHOOTING_STAR_COUNT }, () => {
      const length = 90 + Math.random() * 60;
      const geometry = new THREE.PlaneGeometry(length, 1.6);
      geometry.translate(length / 2, 0, 0);
      const material = new THREE.ShaderMaterial({
        uniforms: { uOpacity: { value: 0 }, uColor: { value: currentColor(theme) } },
        vertexShader: SHOOTING_VERTEX,
        fragmentShader: SHOOTING_FRAGMENT,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      });
      const mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);
      return {
        mesh,
        material,
        active: false,
        startX: 0,
        startY: 0,
        angle: 0,
        travel: 0,
        duration: 0,
        startTime: 0,
        nextSpawn: performance.now() + Math.random() * 4000,
      };
    });

    sceneRef.current = { field, shootingStars };

    function spawn(star: ShootingStar, now: number) {
      const angleDeg = -60 - Math.random() * 20;
      star.angle = (angleDeg * Math.PI) / 180;
      star.startX = width * (0.55 + Math.random() * 0.45);
      star.startY = height * (0.85 + Math.random() * 0.4);
      star.travel = 140 + Math.random() * 120;
      star.duration = 550 + Math.random() * 400;
      star.startTime = now;
      star.active = true;
      star.mesh.position.set(star.startX, star.startY, 0);
      star.mesh.rotation.z = star.angle;
    }

    function updateShootingStars(now: number) {
      for (const star of shootingStars) {
        if (!star.active) {
          if (now >= star.nextSpawn) spawn(star, now);
          continue;
        }
        const t = (now - star.startTime) / star.duration;
        if (t >= 1) {
          star.active = false;
          star.material.uniforms.uOpacity.value = 0;
          star.nextSpawn = now + 2500 + Math.random() * 5000;
          continue;
        }
        const dist = t * star.travel;
        star.mesh.position.set(
          star.startX + Math.cos(star.angle) * dist,
          star.startY + Math.sin(star.angle) * dist,
          0,
        );
        const fadeIn = Math.min(1, t / 0.15);
        const fadeOut = Math.min(1, (1 - t) / 0.35);
        star.material.uniforms.uOpacity.value = Math.min(fadeIn, fadeOut) * 0.9;
      }
    }

    let running = !document.hidden;
    function handleVisibility() {
      running = !document.hidden;
    }
    document.addEventListener("visibilitychange", handleVisibility);

    function handleResize() {
      width = hero!.clientWidth;
      height = hero!.clientHeight;
      camera.right = width;
      camera.top = height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    }
    window.addEventListener("resize", handleResize);

    let rafId = 0;
    function tick(now: number) {
      rafId = requestAnimationFrame(tick);
      if (!running) return;
      field.material.uniforms.uTime.value = now / 1000;
      updateShootingStars(now);
      renderer.render(scene, camera);
    }
    rafId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", handleResize);
      document.removeEventListener("visibilitychange", handleVisibility);
      disposeTwinklingField(field);
      for (const star of shootingStars) {
        star.mesh.geometry.dispose();
        star.material.dispose();
      }
      renderer.dispose();
      sceneRef.current = null;
    };
    // Deliberately mount-only: theme changes are handled by the effect
    // below without tearing down the whole scene.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Live theme reactivity, no scene rebuild.
  useEffect(() => {
    const s = sceneRef.current;
    if (!s) return;
    const color = currentColor(theme);
    s.field.material.uniforms.uColor.value = color;
    for (const star of s.shootingStars) {
      star.material.uniforms.uColor.value = color;
    }
  }, [theme]);

  return <canvas id="heroCanvas" ref={canvasRef} />;
}
