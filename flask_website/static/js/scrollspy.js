// scrollspy.js — windowed accordion: the module you're reading and its
// two neighbors are open; everything further away is folded.
//
// Why this is smooth: the block you scroll toward is ALWAYS already open
// (it was opened invisibly, off-screen, when it entered the window one
// step earlier). Every open/close happens at the window's edges, outside
// the viewport, with the scroll position compensated by measurement — so
// the layout near the reader never changes and scrolling stays native.
//
// Without JavaScript every block stays fully expanded.

// Below this width the windowed accordion is a liability rather than a
// feature: the viewport holds barely one module, so folding neighbours
// shifts the page under the reader's thumb as they scroll. Phones show the
// list open and leave the scroll position alone.
var PHONE_WIDTH = 560;

function isPhone() {
    return window.innerWidth <= PHONE_WIDTH;
}

(function () {
    var index = document.getElementById("module-index");
    if (!index || !("IntersectionObserver" in window)) return;

    document.documentElement.classList.add("js");

    var modules = Array.prototype.slice.call(
        document.querySelectorAll(".module[id]"));
    if (!modules.length) return;

    var links = index.querySelectorAll("a[data-target]");
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute("data-target")] = a; });

    var suppress = false;
    var filterOn = false;

    function setOpen(mod, open) {
        mod.classList.toggle("open", open);
    }

    // "Reopening" for a block ABOVE the reading position: the fold's
    // SPACE snaps open in the same compensated frame as everything else
    // (layout touched exactly once — nothing can fight the trackpad),
    // while the CONTENT fades and settles in over half a second. The
    // reader sees the module smoothly materialize as they arrive.

    // Make {i-1, i, i+1} the open window, anchored so the reader's view
    // does not move a pixel. Blocks BELOW the current module open with
    // the gentle animation (visible as a soft unfold further down the
    // page); everything else changes instantly, off-screen.
    function applyWindow(i, instantAll) {
        // Phones read the page as one continuous list. Folding blocks as
        // the reader moves means compensating the scroll position on every
        // change, and on a touch screen that compensation fights the finger
        // - which is what made scrolling back up stick.
        if (isPhone()) return;
        var anchor = modules[i];
        var topBefore = anchor.getBoundingClientRect().top;
        var touched = [];
        modules.forEach(function (m, j) {
            var shouldOpen = Math.abs(j - i) <= 1;
            var isOpen = m.classList.contains("open");
            if (shouldOpen === isOpen) return;
            if (!shouldOpen && !instantAll) {
                // NEVER close a block the reader can see — defer until
                // it has left the viewport (a later pass gets it).
                var r = m.getBoundingClientRect();
                if (r.bottom > 0 && r.top < window.innerHeight) return;
            }
            if (!instantAll && shouldOpen && j < i) {
                m.classList.add("no-anim-fold");   // height snaps (comped),
                touched.push(m);                    // content fades in
                m.classList.add("in");
                setOpen(m, true);
                return;
            }
            var animate = !instantAll && shouldOpen && j > i;
            if (!animate) {
                m.classList.add("no-anim-self");
                touched.push(m);
            }
            if (shouldOpen) m.classList.add("in");
            setOpen(m, shouldOpen);
        });
        var diff = anchor.getBoundingClientRect().top - topBefore;
        if (diff) {
            window.scrollBy({ top: diff, left: 0, behavior: "instant" });
        }
        if (touched.length) {
            requestAnimationFrame(function () {
                touched.forEach(function (m) {
                    m.classList.remove("no-anim-self");
                    m.classList.remove("no-anim-fold");
                });
            });
        }
    }

    // ---- Scroll-spy: current module = header most recently past a
    // reading line 30% down the viewport (monotonic — cannot flap). ----
    var current = -1;

    function setCurrent(i) {
        if (current === i) return;
        current = i;
        var id = modules[i].id;
        links.forEach(function (a) { a.classList.remove("current"); });
        var link = byId[id];
        if (link) {
            link.classList.add("current");
            link.scrollIntoView({ block: "nearest" });
        }
        if (!suppress) applyWindow(i, false);
    }

    function computeCurrent() {
        if (suppress || filterOn) return;
        // At (or within a hair of) the page bottom, the last module is
        // current by definition — the header-line rule can't always
        // reach it, depending on viewport height.
        var doc = document.documentElement;
        if (window.scrollY + window.innerHeight >= doc.scrollHeight - 4) {
            setCurrent(modules.length - 1);
            return;
        }
        // Adaptive reading line: at most 600px of content is required
        // below a header for it to become current, so tall viewports
        // can still reach the final modules.
        var vh = window.innerHeight;
        var line = Math.max(vh * 0.3, vh - 600);
        var best = 0;
        for (var i = 0; i < modules.length; i++) {
            var head = modules[i].querySelector(".module-head") || modules[i];
            if (head.getBoundingClientRect().top <= line) best = i;
            else break;
        }
        setCurrent(best);
    }

    // Continuous tidy-up: any open block outside the window that has
    // fully left the viewport folds immediately (measured first, closed
    // second, scroll compensated — invisible). This keeps the trail
    // behind the reader collapsing promptly in both directions instead
    // of waiting for the next window shift.
    function tidyOutside() {
        if (isPhone() || suppress || filterOn || current < 0) return;
        var toClose = [];
        modules.forEach(function (m, j) {
            if (!m.classList.contains("open")) return;
            if (Math.abs(j - current) <= 1) return;
            var r = m.getBoundingClientRect();
            if (r.bottom <= 0 || r.top >= window.innerHeight) toClose.push(m);
        });
        if (!toClose.length) return;
        var anchor = modules[current];
        var topBefore = anchor.getBoundingClientRect().top;
        toClose.forEach(function (m) {
            m.classList.add("no-anim-self");
            setOpen(m, false);
        });
        var diff = anchor.getBoundingClientRect().top - topBefore;
        if (diff) {
            window.scrollBy({ top: diff, left: 0, behavior: "instant" });
        }
        requestAnimationFrame(function () {
            toClose.forEach(function (m) {
                m.classList.remove("no-anim-self");
            });
        });
    }

    var ticking = false;
    function onScroll() {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(function () {
            ticking = false;
            computeCurrent();
            tidyOutside();
        });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });

    // ---- Initial state: window around the top (or a deep link) ----
    var startIdx = 0;
    if (location.hash) {
        var t = document.getElementById(location.hash.slice(1));
        var ti = modules.indexOf(t);
        if (ti >= 0) startIdx = ti;
    }
    modules.forEach(function (m, j) {
        var open = isPhone() || Math.abs(j - startIdx) <= 1;
        setOpen(m, open);
        if (open) m.classList.add("in");
    });
    current = startIdx;

    // Deep link: align instantly and hold the scroll-spy off until the
    // landing settles — otherwise the browser's own (smooth) anchor
    // scroll races the window logic and lands mid-page.
    if (startIdx > 0) {
        suppress = true;
        var landing = modules[startIdx];
        requestAnimationFrame(function () {
            landing.scrollIntoView({ behavior: "instant", block: "start" });
            setTimeout(function () {
                landing.scrollIntoView({ behavior: "instant", block: "start" });
                setTimeout(function () { suppress = false; }, 150);
            }, 80);
        });
    }

    // ---- Header click: recenter the window on that module (fallback
    // so any block is always one click from open, whatever the
    // viewport geometry). ----
    modules.forEach(function (mod, i) {
        var head = mod.querySelector(".module-head");
        if (!head) return;
        head.setAttribute("tabindex", "0");
        function activate() {
            mod.classList.add("in");
            applyWindow(i, false);
            current = i;
            links.forEach(function (l) { l.classList.remove("current"); });
            var link = byId[mod.id];
            if (link) link.classList.add("current");
            if (isPhone()) {
                // Land the heading the reader tapped at the top of the
                // screen. Without this the block opened a third of the way
                // down, under the tail of the one before it.
                mod.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        }
        head.addEventListener("click", activate);
        head.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); activate(); }
        });
    });

    // ---- Index links: jump straight to that module, window applied ----
    index.addEventListener("click", function (e) {
        var a = e.target.closest("a[data-target]");
        if (!a) return;
        e.preventDefault();
        var mod = document.getElementById(a.getAttribute("data-target"));
        var i = modules.indexOf(mod);
        if (i < 0) return;
        suppress = true;
        mod.classList.add("in");
        applyWindow(i, true);
        mod.scrollIntoView({ behavior: "instant", block: "start" });
        history.replaceState(null, "", "#" + mod.id);
        current = i;
        links.forEach(function (l) { l.classList.remove("current"); });
        a.classList.add("current");
        requestAnimationFrame(function () {
            mod.scrollIntoView({ behavior: "instant", block: "start" });
            setTimeout(function () { suppress = false; }, 150);
        });
    });

    // ---- Scroll-in reveal (transform/opacity only) ----
    var revealer = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
            if (e.isIntersecting) {
                e.target.classList.add("in");
                revealer.unobserve(e.target);
            }
        });
    }, { rootMargin: "0px 0px -10% 0px" });

    modules.forEach(function (el, i) {
        if (Math.abs(i - startIdx) <= 1) return;
        el.classList.add("reveal");
        revealer.observe(el);
    });

// ---------------- Tag filter: click a pill to see every project
    // using that technology; click it again (or the clear chip) to reset.
    var filterBar = document.createElement("div");
    filterBar.className = "filter-bar";
    filterBar.innerHTML = 'Showing projects using <span class="filter-tag"></span>' +
        '<button type="button" class="filter-clear">Clear &#215;</button>';
    var modulesWrap = document.querySelector(".modules");
    if (modulesWrap) modulesWrap.parentNode.insertBefore(filterBar, modulesWrap);
    var filterLabel = filterBar.querySelector(".filter-tag");
    var activeTag = null;

    // Where the reader was when the filter went on, so clearing puts them
    // back rather than at the top of the page. Stored as a module id plus
    // the offset it sat at, not a raw scroll position: filtering changes
    // the height of everything above, so a pixel value would be meaningless
    // by the time it was restored.
    var restorePoint = null;

    function anchorModule() {
        var best = null;
        var bestTop = Infinity;
        modules.forEach(function (m) {
            var top = m.getBoundingClientRect().top;
            if (Math.abs(top) < Math.abs(bestTop)) {
                bestTop = top;
                best = m;
            }
        });
        return best ? { id: best.id, offset: 24 } : null;
    }

    function scrollToModule(id, offset) {
        var el = document.getElementById(id);
        if (!el) return false;
        var y = window.scrollY + el.getBoundingClientRect().top - offset;
        window.scrollTo({ top: Math.max(0, y), behavior: "instant" });
        return true;
    }

    function clearFilter() {
        var point = restorePoint;
        activeTag = null;
        filterOn = false;
        restorePoint = null;
        filterBar.classList.remove("show");
        document.body.classList.remove("filtering");
        modules.forEach(function (m) { m.style.display = ""; });
        document.querySelectorAll(".tag.active").forEach(function (t) {
            t.classList.remove("active");
        });

        // Reopen the window around whichever module the reader came from, so
        // the block they were reading is expanded when they land back on it.
        var index = current;
        if (point) {
            modules.forEach(function (m, i) { if (m.id === point.id) index = i; });
        }
        index = Math.max(0, Math.min(index, modules.length - 1));
        current = index;
        suppress = true;
        // Snap the folds rather than animating them, so the heights above
        // the reader are final before the position is set. Animating here
        // meant the page kept growing under a scroll that had already been
        // applied, and they landed hundreds of pixels away.
        if (modulesWrap) modulesWrap.classList.add("no-anim");
        applyWindow(index, true);
        if (!point || !scrollToModule(point.id, point.offset)) {
            window.scrollTo({ top: 0, behavior: "instant" });
        }
        // Rather than guess when the layout has finished moving, keep
        // re-asserting the position each frame until it stops changing.
        // Heights above the reader settle over several frames as folds open
        // and the dataset band comes back; a single correction, however
        // late, lands on whatever the page happened to be doing that frame.
        var tries = 0;
        (function settle() {
            if (!point) {
                window.scrollTo({ top: 0, behavior: "instant" });
            } else {
                var before = Math.round(window.scrollY);
                scrollToModule(point.id, point.offset);
                if (Math.round(window.scrollY) === before && tries > 2) {
                    if (modulesWrap) modulesWrap.classList.remove("no-anim");
                    requestAnimationFrame(function () { suppress = false; });
                    return;
                }
            }
            if (++tries > 40) {
                if (modulesWrap) modulesWrap.classList.remove("no-anim");
                suppress = false;
                return;
            }
            requestAnimationFrame(settle);
        })();
    }

    function applyFilter(tag) {
        // Only capture on the way in - switching from one tag to another
        // should still return to where the reader started.
        if (!filterOn) restorePoint = anchorModule();
        activeTag = tag;
        filterOn = true;
        filterLabel.textContent = tag;
        filterBar.classList.add("show");
        document.body.classList.add("filtering");
        var needle = tag.toLowerCase();
        modules.forEach(function (m) {
            var hit = Array.prototype.some.call(
                m.querySelectorAll(".tag"),
                function (t) { return t.textContent.trim().toLowerCase() === needle; });
            m.style.display = hit ? "" : "none";
            if (hit) {
                m.classList.add("in");
                m.classList.add("no-anim-self");
                setOpen(m, true);
            }
        });
        requestAnimationFrame(function () {
            modules.forEach(function (m) { m.classList.remove("no-anim-self"); });
        });
        document.querySelectorAll(".tag").forEach(function (t) {
            t.classList.toggle("active",
                t.textContent.trim().toLowerCase() === needle);
        });
        // Land on the filter bar, not the top of the page. Scrolling to zero
        // put the page head and the dataset band on screen and left the bar
        // below the fold, so a tag matching one project looked like it had
        // simply thrown the reader back to the top with nothing to show.
        var barTop = window.scrollY + filterBar.getBoundingClientRect().top - 16;
        window.scrollTo({ top: Math.max(0, barTop), behavior: "instant" });
    }

    // A ?tool= parameter (from the homepage stack) applies on arrival.
    try {
        var wanted = new URLSearchParams(location.search).get("tool");
        if (wanted) {
            applyFilter(wanted);
        }
    } catch (err) { /* no-op */ }

    document.addEventListener("click", function (e) {
        var t = e.target.closest(".module-tags .tag");
        if (t) {
            var tag = t.textContent.trim();
            if (activeTag && activeTag.toLowerCase() === tag.toLowerCase()) {
                clearFilter();
            } else {
                applyFilter(tag);
            }
            return;
        }
        if (e.target.closest(".filter-clear")) clearFilter();
    });

    // ---------------- Click-to-load embeds (live demos) ----------------
    function loadEmbed(box) {
        if (box.classList.contains("loaded")) return;
        var frame = document.createElement("iframe");
        frame.src = box.getAttribute("data-embed-url");
        frame.loading = "lazy";
        frame.title = "Live demo";
        frame.setAttribute("allow", "clipboard-write");
        box.classList.add("loaded");
        box.replaceChildren(frame);
    }

    // Bring the demo to the top of the viewport once it loads, so the app
    // sits in view instead of wherever the reader happened to be standing.
    // Scroll the demo itself to the top of the viewport, not the module it
    // belongs to: the module's heading, overview and tags are about 400px
    // tall, so aligning on those pushed the app half off the bottom of the
    // screen and the reader had to scroll again to reach the button. The
    // frame is shorter than a laptop viewport, so anchoring on the frame
    // puts the whole app in view at once. Two frames of delay let the
    // accordion finish opening before the position is read.
    function revealEmbed(box) {
        loadEmbed(box);
        // The accordion compensates scroll whenever a block folds, and those
        // instant scrollBy calls cancel a smooth scroll that is still in
        // flight — which is why an earlier version issued the right target
        // and then sat exactly where it started. Suppressing the window
        // logic for the duration lets this one land.
        suppress = true;
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                var rect = box.getBoundingClientRect();
                var slack = Math.max(0, (window.innerHeight - rect.height) / 2);
                window.scrollTo({
                    top: window.scrollY + rect.top - Math.min(slack, 16),
                    behavior: "smooth"
                });
                setTimeout(function () { suppress = false; }, 900);
            });
        });
    }

    // A phone cannot hold the demo inside the page. The app stacks further
    // at this width and runs taller than any frame that still fits, and an
    // iframe taller than its box cannot be scrolled from inside a scrolling
    // page on iOS — so the bottom of the app was simply unreachable. Phones
    // open it in its own tab, where it gets the whole screen. The threshold
    // matches the stylesheet's phone breakpoint.
    var EMBED_INLINE_MIN = 621;

    function embedFitsInline() {
        return window.innerWidth >= EMBED_INLINE_MIN;
    }

    document.querySelectorAll(".embed").forEach(function (box) {
        var btn = box.querySelector(".embed-cta");
        if (!btn) return;
        // Marked at load so the button carries the outbound arrow before it
        // is pressed, rather than surprising the reader with a new tab.
        if (!embedFitsInline()) box.classList.add("embed-external");
        btn.addEventListener("click", function () {
            if (embedFitsInline()) {
                revealEmbed(box);
                return;
            }
            window.open(box.getAttribute("data-embed-url"), "_blank", "noopener");
        });

        // "Try it live" is left alone: it opens the Space on Hugging Face in
        // a new tab. Running the model in place is what the panel below is
        // for, so the two offer a real choice rather than the same thing.
    });

})();

// ---------------- Lightbox: click a screenshot to view it full-size --------
//
// A separate top-level block, not nested inside the accordion above. The
// accordion returns early when a page has no module blocks — which is every
// case-study page — and while it was nested that return took the lightbox
// with it, so the screenshots on those pages were not clickable at all.
(function () {
    var strips = document.querySelectorAll(".module-strip img, .case-shots img");
    if (!strips.length) return;

    var box = document.createElement("div");
    box.className = "lightbox";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-label", "Screenshot viewer");
    // The <img> is created on first open rather than up front: an empty,
    // sizeless image sitting in the DOM from page load is a real audit
    // failure and reserves nothing useful in the meantime.
    box.innerHTML = '<div class="lightbox-cap"></div>';
    document.body.appendChild(box);
    var cap = box.querySelector(".lightbox-cap");
    var big = null;

    function openBox(img) {
        if (!big) {
            big = document.createElement("img");
            box.insertBefore(big, cap);
        }
        // Declare the box's size before the full image arrives, and use the
        // full file rather than the thumbnail the strip serves.
        big.width = img.naturalWidth || img.width;
        big.height = img.naturalHeight || img.height;
        big.src = img.getAttribute("data-full") || img.src;
        var alt = img.alt;
        big.alt = alt || "Enlarged project screenshot";
        cap.textContent = alt || "";
        box.classList.add("show");
        document.body.style.overflow = "hidden";
    }
    function closeBox() {
        box.classList.remove("show");
        document.body.style.overflow = "";
    }
    strips.forEach(function (img) {
        img.setAttribute("tabindex", "0");
        img.setAttribute("role", "button");
        img.addEventListener("click", function () { openBox(img); });
        img.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openBox(img);
            }
        });
    });
    box.addEventListener("click", closeBox);
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeBox();
    });
})();
