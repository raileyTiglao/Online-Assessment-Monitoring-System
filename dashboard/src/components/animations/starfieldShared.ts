// src/components/animations/starfieldShared.ts — shared point-cloud
// factory for HeroStarfield and ThemeToggleStarfield. Both render a field
// of twinkling points with the same shader technique (soft circle +
// sine-wave twinkle), just different counts/sizes — this avoids
// duplicating the shader source in two files.

import * as THREE from "three";

const VERTEX_SHADER = `
  attribute float aSize;
  attribute float aPhase;
  varying float vPhase;
  void main() {
    vPhase = aPhase;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = aSize;
    gl_Position = projectionMatrix * mvPosition;
  }
`;

// twinkleSpeed/twinkleFloor/twinkleGain/alphaCap let HeroStarfield (90
// slower, dimmer points) and ThemeToggleStarfield (20 faster, brighter
// points) share this shader with slightly different twinkle character,
// matching the source design's two hand-tuned variants.
function fragmentShader(twinkleSpeed: number, twinkleFloor: number, twinkleGain: number, alphaCap: number) {
  return `
    uniform float uTime;
    uniform vec3 uColor;
    varying float vPhase;
    void main() {
      float dist = length(gl_PointCoord - vec2(0.5));
      float circle = smoothstep(0.5, 0.0, dist);
      float twinkle = ${twinkleFloor.toFixed(3)} + ${twinkleGain.toFixed(3)} * (0.5 + 0.5 * sin(uTime * ${twinkleSpeed.toFixed(3)} + vPhase));
      gl_FragColor = vec4(uColor, circle * twinkle * ${alphaCap.toFixed(3)});
    }
  `;
}

export interface TwinklingField {
  points: THREE.Points;
  material: THREE.ShaderMaterial;
}

export function createTwinklingStars(
  count: number,
  width: number,
  height: number,
  color: THREE.Color,
  sizeRange: [number, number],
  shaderTuning: { speed: number; floor: number; gain: number; alphaCap: number },
): TwinklingField {
  const positions = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);

  for (let i = 0; i < count; i++) {
    positions[i * 3] = Math.random() * width;
    positions[i * 3 + 1] = Math.random() * height;
    positions[i * 3 + 2] = 0;
    sizes[i] = sizeRange[0] + Math.random() * (sizeRange[1] - sizeRange[0]);
    phases[i] = Math.random() * Math.PI * 2;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  geometry.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));

  const material = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: color },
    },
    vertexShader: VERTEX_SHADER,
    fragmentShader: fragmentShader(
      shaderTuning.speed,
      shaderTuning.floor,
      shaderTuning.gain,
      shaderTuning.alphaCap,
    ),
    transparent: true,
    depthWrite: false,
  });

  return { points: new THREE.Points(geometry, material), material };
}

export function disposeTwinklingField(field: TwinklingField) {
  field.points.geometry.dispose();
  field.material.dispose();
}
