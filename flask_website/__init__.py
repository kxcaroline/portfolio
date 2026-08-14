"""Application factory - creates and configures the Flask app."""

import gzip
from pathlib import Path

from flask import Flask, render_template, request, url_for

from flask_website.pages import pages

# Below this, the gzip header costs more than the compression saves.
COMPRESS_MIN_BYTES = 1024
# Ceiling on what is worth buffering into memory to compress.
COMPRESS_MAX_BYTES = 2 * 1024 * 1024
COMPRESSIBLE = ("text/html", "text/css", "application/javascript",
                "text/javascript", "application/json", "image/svg+xml")

# How long a static file may be reused, decided by whether its URL
# identifies a specific version of it. A stamped URL (style.min.css?v=...)
# names one exact revision - the stamp changes the moment the file does - so
# the answer can be cached for a year and never revalidated. An unstamped
# one names whatever is at that path today, so it gets a day.
STAMPED_MAX_AGE = 31536000      # one year
UNSTAMPED_MAX_AGE = 86400       # one day

# Response headers that cost nothing and close off a few default behaviours
# the site never wants.
#
# nosniff: a file is what its Content-Type says it is, so a .webp can never
#   be reinterpreted as script.
# Referrer-Policy: an outbound click carries this site's origin but not
#   which page the visitor was reading.
# Permissions-Policy: a portfolio has no business asking for a camera, a
#   microphone or a location, so the page gives up the right to.
# X-Frame-Options: the site embeds a demo; nothing needs to embed the site,
#   and refusing makes clickjacking a non-question.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), "
                          "interest-cohort=()",
    "X-Frame-Options": "SAMEORIGIN",
}


def create_app():
    """Build, configure, and return the Flask app."""
    app = Flask(__name__)
    app.config.from_object("flask_website.config.Config")

    # Register the pages blueprint so its routes become active.
    app.register_blueprint(pages.bp)

    # Make the project list available to EVERY template, so the module
    # index can live in the site-wide navigation rail (base.html), not
    # just on the Projects page.
    @app.context_processor
    def inject_modules():
        return {"nav_modules": pages.load_projects()}

    # Cache-busting stamps, derived from the files rather than typed.
    #
    # The stylesheet used to be requested as "style.css?v=59", with the
    # number maintained by hand. Editing the stylesheet without remembering
    # to raise it meant browsers kept serving the copy they already had:
    # the deploy was correct and the change was invisible, which is the
    # worst kind of wrong. Stamping with the file's modification time makes
    # the URL change exactly when the file does, and never otherwise.
    stamps = {}

    @app.template_global("asset")
    def asset(filename):
        """URL for a static file, stamped with its modification time.

        A ``.min`` sibling is preferred when it exists and is at least as
        new as its source, so the readable stylesheet stays the file in the
        repository while visitors get the compact one. Editing the source
        and forgetting to rebuild makes the sibling stale, and a stale
        sibling is ignored rather than served — the failure mode is a
        larger download, never a wrong one.
        """
        assert app.static_folder is not None
        root = Path(app.static_folder)
        stem, dot, ext = filename.rpartition(".")
        if dot and ext in ("css", "js"):
            minified = f"{stem}.min.{ext}"
            try:
                if (root / minified).stat().st_mtime >= (root / filename).stat().st_mtime:
                    filename = minified
            except OSError:
                pass
        url = url_for("static", filename=filename)
        if app.debug or filename not in stamps:
            # static_folder is Optional in Flask's types because an app can
            # disable static serving; this one never does.
            assert app.static_folder is not None
            try:
                stamps[filename] = int((Path(app.static_folder) / filename)
                                       .stat().st_mtime)
            except OSError:
                # No file to stamp: return the plain URL rather than a
                # stamp that would be wrong.
                return url
        return f"{url}?v={stamps[filename]}"

    @app.after_request
    def cache_static(response):
        """Set Cache-Control on static responses."""
        if request.endpoint != "static" or response.status_code != 200:
            return response
        # Font filenames carry family, weight, style and subset, so the
        # name is the identity: a different face is a different file.
        versioned = request.args.get("v") or request.path.startswith(
            "/static/fonts/")
        if versioned:
            response.headers["Cache-Control"] = (
                f"public, max-age={STAMPED_MAX_AGE}, immutable")
        else:
            response.headers["Cache-Control"] = (
                f"public, max-age={UNSTAMPED_MAX_AGE}, must-revalidate")
        return response

    # Text assets go over the wire compressed. The stylesheet is the only
    # render-blocking resource on the page and it is the largest text file
    # the site serves; gzip takes it from ~50KB to ~13KB.
    @app.after_request
    def compress(response):
        accepted = request.headers.get("Accept-Encoding", "")
        # One guard, one meaning: "is this response compressible?" Splitting
        # the chain into nested ifs would score better and read worse.
        # pylint: disable-next=too-many-boolean-expressions
        if ("gzip" not in accepted
                or response.status_code < 200
                or response.status_code >= 300
                or "Content-Encoding" in response.headers
                or response.mimetype not in COMPRESSIBLE
                or response.content_length is None
                or not COMPRESS_MIN_BYTES <= response.content_length <= COMPRESS_MAX_BYTES):
            return response
        # Static files stream from disk; reading the body turns that off,
        # which is why the size ceiling above exists.
        response.direct_passthrough = False
        response.set_data(gzip.compress(response.get_data(), 6))
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = response.content_length
        response.headers.add("Vary", "Accept-Encoding")
        return response

    @app.after_request
    def security_headers(response):
        """Attach the site-wide response headers."""
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    # Branded 404 instead of the bare default page.
    @app.errorhandler(404)
    def page_not_found(_error):
        return render_template("404.html", active=None), 404

    return app
