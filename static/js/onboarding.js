(function () {
    const shell = document.querySelector('[data-onboarding-shell]');
    if (!shell) return;

    const slides = Array.from(shell.querySelectorAll('[data-onboarding-step]'));
    const dots = Array.from(shell.querySelectorAll('[data-onboarding-dot]'));
    const prev = shell.querySelector('[data-onboarding-prev]');
    const next = shell.querySelector('[data-onboarding-next]');
    let index = Number.parseInt(shell.dataset.initialStep || '0', 10);
    if (Number.isNaN(index)) index = 0;

    function showSlide(nextIndex) {
        index = Math.max(0, Math.min(slides.length - 1, nextIndex));

        slides.forEach((slide, slideIndex) => {
            slide.classList.toggle('is-active', slideIndex === index);
        });

        dots.forEach((dot, dotIndex) => {
            dot.classList.toggle('is-active', dotIndex === index);
        });

        if (prev) prev.disabled = index === 0;
        if (next) {
            next.textContent = index === slides.length - 1 ? 'Completar ficha' : 'Siguiente';
        }
    }

    if (prev) {
        prev.addEventListener('click', function () {
            showSlide(index - 1);
        });
    }

    if (next) {
        next.addEventListener('click', function () {
            if (index === slides.length - 1) {
                const firstInput = shell.querySelector('.onboarding-slide--form input, .onboarding-slide--form select');
                if (firstInput) firstInput.focus();
                return;
            }
            showSlide(index + 1);
        });
    }

    dots.forEach((dot, dotIndex) => {
        dot.addEventListener('click', function () {
            showSlide(dotIndex);
        });
    });

    showSlide(index);
})();
