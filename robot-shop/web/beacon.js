(function () {
    let maxScroll = 0, activeMs = 0, last = Date.now(), visible = true;

    window.addEventListener("scroll", () => {
        const s = document.body.scrollHeight || document.documentElement.scrollHeight;
        if (s > 0) maxScroll = Math.max(maxScroll, (window.scrollY + window.innerHeight) / s);
    });

    document.addEventListener("visibilitychange", () => {
        const now = Date.now();
        if (visible) activeMs += now - last;
        visible = (document.visibilityState === "visible");
        last = now;
    });

    let seen = false;
    const target = document.querySelector("#product-main") || document.body;
    if (target) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach(e => { if (e.isIntersecting) seen = true; });
        });
        io.observe(target);
    }

    setInterval(() => {
        navigator.sendBeacon("/beacon", JSON.stringify({
            sid: window.__sid || "anonymous",
            maxScroll: Number(maxScroll.toFixed(2)),
            activeMs,
            shown: seen
        }));
    }, 5000);
})();