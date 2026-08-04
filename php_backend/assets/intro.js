(() => {
    // Ported from the beta star-shower intro. Ships once per browser tab
    // session (sessionStorage flag) rather than on every full-page
    // navigation — OAMS is a multi-page app (not an SPA), and replaying a
    // 2.6s locked overlay on every click through Sessions/Exams/etc. would
    // be friction, not delight.
    const overlay = document.getElementById('introOverlay');
    const field = document.getElementById('introField');
    if (!overlay || !field) return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let alreadyShown = false;
    try { alreadyShown = sessionStorage.getItem('oams-intro-shown') === '1'; } catch (e) {}

    if (reduceMotion || alreadyShown) {
        overlay.remove();
        return;
    }

    const STAR_COUNT = 18;
    const DOT_COUNT = 90;
    const SHOWER_DURATION = 2600;

    function rand(min, max) {
        return min + Math.random() * (max - min);
    }

    function buildStar(index) {
        const depth = Math.random();
        const size = rand(14, 74) * (0.5 + depth * 0.5);
        const tailWidth = size * rand(3.2, 4.8);
        const tailHeight = tailWidth * 0.26;

        const startX = rand(30, 135);
        const startY = rand(-20, 55);
        const distance = rand(70, 110);

        const star = document.createElement('div');
        star.className = 'intro-star';
        star.style.left = `${startX}vw`;
        star.style.top = `${startY}vh`;
        star.style.setProperty('--star-size', `${size}px`);
        star.style.setProperty('--tail-width', `${tailWidth}px`);
        star.style.setProperty('--tail-height', `${tailHeight}px`);
        star.style.setProperty('--travel-x', `${-distance}vw`);
        star.style.setProperty('--travel-y', `${distance}vh`);
        star.style.setProperty('--travel-duration', `${rand(1.1, 1.9)}s`);
        star.style.setProperty('--travel-delay', `${rand(0, 1.2)}s`);

        const gradientId = `introTailGrad${index}`;
        star.innerHTML = `
            <svg class="intro-star-tail" viewBox="0 0 400 100" preserveAspectRatio="none">
                <defs>
                    <linearGradient id="${gradientId}" x1="100%" y1="0%" x2="0%" y2="0%">
                        <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95"/>
                        <stop offset="45%" stop-color="#ffffff" stop-opacity="0.4"/>
                        <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
                    </linearGradient>
                </defs>
                <path d="M400,22 C322,26 214,40 128,52 C78,59 30,62 0,63 C32,66 82,70 132,75 C216,84 320,92 400,94 Z" fill="url(#${gradientId})"/>
            </svg>
            <svg class="intro-star-core" viewBox="0 0 100 100">
                <path d="M50,0 C50,28 28,50 0,50 C28,50 50,72 50,100 C50,72 72,50 100,50 C72,50 50,28 50,0 Z" fill="#ffffff"/>
            </svg>
        `;
        return star;
    }

    function buildDot() {
        const depth = Math.random();
        const dot = document.createElement('span');
        dot.className = 'intro-dot';
        dot.style.left = `${rand(0, 100)}vw`;
        dot.style.top = `${rand(0, 100)}vh`;
        dot.style.setProperty('--dot-size', `${rand(1.2, 3.4) * (0.6 + depth * 0.4)}px`);
        dot.style.setProperty('--dot-peak', `${rand(0.35, 1)}`);
        dot.style.setProperty('--twinkle-duration', `${rand(1.4, 3.2)}s`);
        dot.style.setProperty('--twinkle-delay', `${rand(0, 2.4)}s`);
        return dot;
    }

    const fragment = document.createDocumentFragment();
    for (let i = 0; i < DOT_COUNT; i++) {
        fragment.appendChild(buildDot());
    }
    for (let i = 0; i < STAR_COUNT; i++) {
        fragment.appendChild(buildStar(i));
    }
    field.appendChild(fragment);

    try { sessionStorage.setItem('oams-intro-shown', '1'); } catch (e) {}

    function dismiss() {
        overlay.classList.add('is-hidden');
        overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
    }
    setTimeout(dismiss, SHOWER_DURATION);
})();
