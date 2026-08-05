(() => {
    // Ported from the beta hero starfield. No-ops on any page without a
    // #heroCanvas (only dashboard.php has one), so it's safe to load
    // globally without adding a canvas per page.
    const canvas = document.getElementById('heroCanvas');
    if (!canvas || typeof THREE === 'undefined') return;

    const hero = canvas.parentElement;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) return;

    const STAR_COUNT = 90;
    const SHOOTING_STAR_COUNT = 3;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    const scene = new THREE.Scene();
    let width = hero.clientWidth;
    let height = hero.clientHeight;
    const camera = new THREE.OrthographicCamera(0, width, height, 0, -10, 10);
    renderer.setSize(width, height, false);

    function resize() {
        width = hero.clientWidth;
        height = hero.clientHeight;
        camera.right = width;
        camera.top = height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
    }
    window.addEventListener('resize', resize);

    const DARK_STAR_COLOR = new THREE.Color(1, 1, 1);
    const LIGHT_STAR_COLOR = new THREE.Color(0.09, 0.16, 0.24);

    function currentThemeColor() {
        return document.documentElement.getAttribute('data-theme') === 'light' ? LIGHT_STAR_COLOR : DARK_STAR_COLOR;
    }

    const starGeometry = new THREE.BufferGeometry();
    const positions = new Float32Array(STAR_COUNT * 3);
    const sizes = new Float32Array(STAR_COUNT);
    const phases = new Float32Array(STAR_COUNT);

    for (let i = 0; i < STAR_COUNT; i++) {
        positions[i * 3] = Math.random() * width;
        positions[i * 3 + 1] = Math.random() * height;
        positions[i * 3 + 2] = 0;
        sizes[i] = 1 + Math.random() * 2;
        phases[i] = Math.random() * Math.PI * 2;
    }

    starGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    starGeometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
    starGeometry.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1));

    const starMaterial = new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        uniforms: { uTime: { value: 0 }, uColor: { value: currentThemeColor() } },
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
                float twinkle = 0.35 + 0.65 * (0.5 + 0.5 * sin(uTime * 2.0 + vPhase));
                gl_FragColor = vec4(uColor, circle * twinkle * 0.85);
            }
        `,
    });

    scene.add(new THREE.Points(starGeometry, starMaterial));

    const streakVertex = `
        varying vec2 vUv;
        void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `;
    const streakFragment = `
        varying vec2 vUv;
        uniform float uOpacity;
        uniform vec3 uColor;
        void main() {
            float head = smoothstep(0.0, 1.0, vUv.x);
            gl_FragColor = vec4(uColor, head * uOpacity);
        }
    `;

    function makeShootingStar() {
        const length = 90 + Math.random() * 60;
        const thickness = 1.6;
        const geometry = new THREE.PlaneGeometry(length, thickness);
        geometry.translate(length / 2, 0, 0);
        const material = new THREE.ShaderMaterial({
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            uniforms: { uOpacity: { value: 0 }, uColor: { value: currentThemeColor() } },
            vertexShader: streakVertex,
            fragmentShader: streakFragment,
        });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);

        return {
            mesh,
            material,
            length,
            active: false,
            startTime: 0,
            duration: 700,
            nextSpawn: performance.now() + Math.random() * 4000,
        };
    }

    const shootingStars = Array.from({ length: SHOOTING_STAR_COUNT }, makeShootingStar);

    function spawn(star, now) {
        const angle = (-60 - Math.random() * 20) * (Math.PI / 180);
        const startX = width * (0.55 + Math.random() * 0.45);
        const startY = height * (0.85 + Math.random() * 0.4);

        star.startX = startX;
        star.startY = startY;
        star.angle = angle;
        star.travel = 140 + Math.random() * 120;
        star.duration = 550 + Math.random() * 400;
        star.startTime = now;
        star.active = true;
        star.mesh.rotation.z = angle;
    }

    function updateShootingStars(now) {
        shootingStars.forEach((star) => {
            if (!star.active) {
                if (now >= star.nextSpawn) spawn(star, now);
                return;
            }

            const t = (now - star.startTime) / star.duration;
            if (t >= 1) {
                star.active = false;
                star.material.uniforms.uOpacity.value = 0;
                star.nextSpawn = now + 2500 + Math.random() * 5000;
                return;
            }

            const dist = t * star.travel;
            const headX = star.startX + Math.cos(star.angle) * dist;
            const headY = star.startY + Math.sin(star.angle) * dist;
            star.mesh.position.set(headX, headY, 0);

            const fadeIn = Math.min(1, t / 0.15);
            const fadeOut = Math.min(1, (1 - t) / 0.35);
            star.material.uniforms.uOpacity.value = Math.min(fadeIn, fadeOut) * 0.9;
        });
    }

    let running = true;
    document.addEventListener('visibilitychange', () => {
        running = document.visibilityState === 'visible';
    });

    document.addEventListener('themechange', () => {
        const color = currentThemeColor();
        starMaterial.uniforms.uColor.value = color;
        shootingStars.forEach((star) => {
            star.material.uniforms.uColor.value = color;
        });
    });

    function tick(now) {
        requestAnimationFrame(tick);
        if (!running) return;
        starMaterial.uniforms.uTime.value = now / 1000;
        updateShootingStars(now);
        renderer.render(scene, camera);
    }

    requestAnimationFrame(tick);
})();
