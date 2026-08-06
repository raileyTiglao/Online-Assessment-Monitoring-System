(() => {
    // Tiny Three.js starfield rendered inside the sidebar theme pill — same
    // twinkling-point technique as hero-stars.js. Dark mode reads as the
    // normal white-on-navy starfield; light mode is an "inverted" reading
    // of the same field (dark ink-colored specks on the gold pill) rather
    // than swapping to an unrelated sun icon.
    const canvas = document.getElementById('themeSwitchCanvas');
    if (!canvas || typeof THREE === 'undefined') return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const width = canvas.clientWidth || 140;
    const height = canvas.clientHeight || 40;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(0, width, height, 0, -10, 10);

    const STAR_COUNT = 20;
    const positions = new Float32Array(STAR_COUNT * 3);
    const sizes = new Float32Array(STAR_COUNT);
    const phases = new Float32Array(STAR_COUNT);
    for (let i = 0; i < STAR_COUNT; i++) {
        positions[i * 3] = Math.random() * width;
        positions[i * 3 + 1] = Math.random() * height;
        positions[i * 3 + 2] = 0;
        sizes[i] = 1 + Math.random() * 1.8;
        phases[i] = Math.random() * Math.PI * 2;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
    geometry.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1));

    // Matches --color-on-hero for each theme (#efe9db dark / #16232e light)
    // so the pill's stars read as the same ink used on the hero panel.
    const DARK_STAR_COLOR = new THREE.Color(0.937, 0.914, 0.859);
    const LIGHT_STAR_COLOR = new THREE.Color(0.086, 0.137, 0.180);

    function currentColor() {
        return document.documentElement.getAttribute('data-theme') === 'light' ? LIGHT_STAR_COLOR : DARK_STAR_COLOR;
    }

    const material = new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        uniforms: { uTime: { value: 0 }, uColor: { value: currentColor() } },
        vertexShader: `
            attribute float aSize;
            attribute float aPhase;
            varying float vPhase;
            void main() {
                vPhase = aPhase;
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = aSize;
            }
        `,
        fragmentShader: `
            uniform float uTime;
            uniform vec3 uColor;
            varying float vPhase;
            void main() {
                vec2 uv = gl_PointCoord - vec2(0.5);
                float circle = smoothstep(0.5, 0.0, length(uv));
                float twinkle = 0.4 + 0.6 * (0.5 + 0.5 * sin(uTime * 2.2 + vPhase));
                gl_FragColor = vec4(uColor, circle * twinkle);
            }
        `,
    });

    scene.add(new THREE.Points(geometry, material));

    document.addEventListener('themechange', () => {
        material.uniforms.uColor.value = currentColor();
    });

    if (reduceMotion) {
        renderer.render(scene, camera);
        return;
    }

    function tick(now) {
        requestAnimationFrame(tick);
        material.uniforms.uTime.value = now / 1000;
        renderer.render(scene, camera);
    }
    requestAnimationFrame(tick);
})();
