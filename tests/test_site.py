"""Tests for the Module 14 portfolio site.

Two kinds of check live here:

*Routing* — every page returns what it should, including the failure
paths (an unknown project, a project without a case study), because a
portfolio that 500s in front of a visitor is worse than one that is
plain.

*Data integrity* — the site is rendered from JSON, so the JSON is the
thing that can silently break it. These tests assert the contract the
templates rely on: keys present, images and their declared dimensions in
step with the files on disk, and every cross-reference resolving. A
mismatch between image_dims and the real files is invisible on screen
but reintroduces layout shift, so it is checked against the pixels
rather than trusted.
"""

import json
import os
import re
from pathlib import Path

import pytest
from PIL import Image

from flask_website import create_app
from flask_website.pages import pages

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "flask_website" / "static" / "images" / "projects"
THUMBS = ROOT / "flask_website" / "static" / "images" / "thumbs"
AREA_KEYS = {key for key, _ in pages.AREA_ORDER}


@pytest.fixture(name="client")
def fixture_client():
    """A test client for the application."""
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture(name="modules", scope="module")
def fixture_modules():
    """The project entries the site renders."""
    return pages.load_projects()


# ---------------------------------------------------------------- routing

@pytest.mark.parametrize("route", ["/", "/projects", "/contact", "/demos/trials"])
def test_pages_render(client, route):
    """Every public page returns 200."""
    assert client.get(route).status_code == 200


def test_case_study_renders_for_modules_that_have_one(client, modules):
    """A module carrying a case entry has a page at /projects/<id>."""
    with_case = [m["id"] for m in modules if m.get("case")]
    assert with_case, "expected at least one case study"
    for module_id in with_case:
        assert client.get(f"/projects/{module_id}").status_code == 200


def test_case_study_404s_without_a_case(client, modules):
    """Modules with no case entry return 404, not an empty shell."""
    without = [m["id"] for m in modules if not m.get("case")]
    assert without, "expected at least one module without a case study"
    assert client.get(f"/projects/{without[0]}").status_code == 404


def test_unknown_project_404s(client):
    """An id that does not exist returns the branded 404."""
    assert client.get("/projects/999").status_code == 404


def test_unknown_path_404s(client):
    """Any unrouted path returns 404 rather than an error page."""
    assert client.get("/no-such-page").status_code == 404


def test_navigation_is_present_on_every_page(client):
    """The context processor supplies the module index site-wide."""
    for route in ("/", "/projects", "/contact"):
        assert b'id="module-index"' in client.get(route).data


# ------------------------------------------------------- data integrity

def test_every_module_has_the_keys_templates_read(modules):
    """The templates index these directly, so a missing key is a 500."""
    required = {"id", "code", "title", "date", "tags", "overview",
                "learned", "images", "image_dims", "area_key", "area"}
    for module in modules:
        missing = required - set(module)
        assert not missing, f"module {module.get('id')} missing {missing}"


def test_module_ids_are_unique(modules):
    """Ids are used as dictionary keys when resolving a case study."""
    ids = [m["id"] for m in modules]
    assert len(ids) == len(set(ids))


def test_area_keys_are_known(modules):
    """An unknown area key would render an uncoloured, unfiltered block."""
    for module in modules:
        assert module["area_key"] in AREA_KEYS


def test_declared_image_dimensions_match_the_files(modules):
    """Wrong dimensions reintroduce layout shift without looking wrong.

    The width and height attributes exist so the browser can reserve
    space before an image loads. If they drift from the real files the
    page still looks correct but the shift returns, so this compares
    against the pixels rather than trusting the JSON.
    """
    for module in modules:
        images, dims = module["images"], module["image_dims"]
        assert len(images) == len(dims), f"module {module['id']}: length mismatch"
        for name, declared in zip(images, dims):
            path = IMAGES / name
            assert path.exists(), f"missing image: {name}"
            assert list(Image.open(path).size) == list(declared), (
                f"{name}: declared {declared}, file is {Image.open(path).size}"
            )


@pytest.mark.parametrize("dims,expected", [
    ([1100, 687], ""),          # ordinary landscape screenshot
    ([918, 1209], ""),          # portrait, still legible fitted
    ([1100, 4344], "thumb-crop"),   # full-page capture
    ([1100, 184], ""),          # wide banner
    (None, ""),                 # no dimensions recorded
])
def test_thumbnails_only_crop_the_captures_that_need_it(dims, expected):
    """Fitting a page capture into a 16:10 tile leaves an unreadable sliver.

    Only images past the tall threshold are cropped to a page preview;
    everything else is fitted whole, because cropping to a common ratio is
    what was slicing screenshots in half.
    """
    assert pages.thumb_class(dims) == expected


def test_every_screenshot_is_labelled(modules):
    """Each thumbnail carries a caption naming what it shows."""
    for module in modules:
        labels = module.get("image_labels")
        assert labels, f"module {module['id']} has no image_labels"
        assert len(labels) == len(module["images"])
        for label in labels:
            assert label.strip() and len(label) <= 20, repr(label)


def test_every_screenshot_has_a_thumbnail(modules):
    """The strip serves thumbnails; a missing one is a broken image.

    The full screenshots are ~1.2MB in total and render at 172px, so the
    strip points at generated thumbnails and only the lightbox fetches the
    original. That makes the thumbnail a required asset rather than an
    optimisation, and a module added without one would show nothing.
    """
    for module in modules:
        for name in module["images"]:
            thumb = THUMBS / name
            assert thumb.exists(), f"missing thumbnail: {name}"
            assert Image.open(thumb).size[0] <= 400, (
                f"{name}: thumbnail is larger than the tile can use"
            )


def test_recorded_thumbnail_sizes_match_the_files(modules):
    """The declared size has to be the served image's, not the original's.

    build_thumbs.py writes these when it writes the images, so the site can
    reserve each box without opening a file. That only holds while the record
    and the images agree - if someone replaces a screenshot without rerunning
    the build, the page reserves the wrong box and the layout shift the
    attributes exist to prevent comes back looking correct.
    """
    for module in modules:
        for name in module["images"]:
            declared = pages.thumb_size(name)
            assert declared is not None, f"no generated thumbnail for {name}"
            assert list(declared) == list(Image.open(THUMBS / name).size)


def test_thumb_size_is_none_when_there_is_no_thumbnail():
    """Missing entry degrades to no attributes rather than wrong ones."""
    assert pages.thumb_size("module_99/nope.webp") is None


def test_thumb_sizes_degrade_when_the_record_is_missing(monkeypatch, tmp_path):
    """A missing or corrupt record omits the attributes, not the page."""
    monkeypatch.setattr(pages, "THUMB_SIZES_FILE", tmp_path / "absent.json")
    assert pages.load_thumb_sizes() == {}
    broken = tmp_path / "broken.json"
    broken.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(pages, "THUMB_SIZES_FILE", broken)
    assert pages.load_thumb_sizes() == {}


def test_case_studies_are_complete(modules):
    """A half-written case object would render blank sections."""
    for module in modules:
        case = module.get("case")
        if not case:
            continue
        assert {"summary", "context", "approach", "challenges",
                "results", "reflection"} <= set(case)
        for challenge in case["challenges"]:
            assert {"problem", "solution"} <= set(challenge)
        for result in case["results"]:
            assert {"value", "label", "note"} <= set(result)


def test_featured_skills_reference_real_modules_and_tags(modules):
    """A featured skill pointing at the wrong module is a broken claim."""
    by_id = {m["id"]: m for m in modules}
    for skill in pages.load_skills():
        assert skill["area_key"] in AREA_KEYS
        module = by_id.get(skill["module"])
        assert module is not None, f"{skill['name']} cites a missing module"
        assert skill["name"] in module["tags"], (
            f"{skill['name']} is not a tag on module {skill['module']}"
        )


def test_no_tag_is_silently_dropped(modules):
    """Every tag appears somewhere: featured, data source, or the tail."""
    built = pages.build_skills(modules)
    shown = ({s["name"] for g in built["groups"] for s in g["items"]}
             | {e["name"] for e in built["rest"]}
             | {e["name"] for e in built["data_sources"]})
    all_tags = {t for m in modules for t in m["tags"]}
    assert all_tags == shown


# --------------------------------------------------- graceful degradation

def test_missing_stats_file_does_not_break_projects(client, monkeypatch):
    """The figure is optional; the page is not."""
    monkeypatch.setattr(pages, "load_stats", lambda: None)
    assert client.get("/projects").status_code == 200


@pytest.mark.parametrize("broken", [
    {},                                        # no keys at all
    {"records": 1, "universities": 1, "programs": 1},   # no curve
    {"records": 1, "universities": 1, "programs": 1,
     "gpa_curve": [{"gpa": 3.0}]},             # curve entries incomplete
])
def test_incomplete_stats_are_rejected_not_rendered(client, monkeypatch, broken):
    """A structurally incomplete stats file omits the figure, not the page.

    Valid JSON with the wrong shape used to reach the view and raise a
    KeyError, which is the failure mode a half-finished build produces.
    """
    monkeypatch.setattr(pages, "load_stats", lambda: broken)
    assert client.get("/projects").status_code == 200


# ------------------------------------------------------------- transport

def test_assets_are_stamped_with_their_modification_time(client):
    """The cache-buster comes from the file, not from a number in a template.

    Hand-maintained version numbers drift: editing the stylesheet without
    raising the number leaves browsers serving the copy they already have,
    so a correct deploy produces no visible change. Stamping with mtime
    makes the URL change exactly when the file does.
    """
    css = ROOT / "flask_website" / "static" / "css" / "style.min.css"
    expected = int(css.stat().st_mtime)
    page = client.get("/").data.decode()
    assert f"css/style.min.css?v={expected}" in page


def test_asset_stamp_follows_a_changed_file():
    """Touching a file changes its URL; leaving it alone does not."""
    app = create_app()
    app.config.update(TESTING=True)
    target = ROOT / "flask_website" / "static" / "js" / "scrollspy.min.js"
    with app.test_request_context():
        first = app.jinja_env.globals["asset"]("js/scrollspy.js")
        again = app.jinja_env.globals["asset"]("js/scrollspy.js")
    assert first == again
    assert f"?v={int(target.stat().st_mtime)}" in first


def test_missing_asset_degrades_to_an_unstamped_url():
    """A stamp that cannot be read is omitted, not guessed."""
    app = create_app()
    with app.test_request_context():
        url = app.jinja_env.globals["asset"]("css/does-not-exist.css")
    assert url.endswith("does-not-exist.css")
    assert "?v=" not in url


def test_text_responses_are_compressed(client):
    """The stylesheet is the only render-blocking asset on the page.

    Uncompressed it is ~40KB and the largest text file the site serves;
    gzip takes it to roughly a quarter of that, which buys more than
    minifying the source would and leaves the CSS readable.
    """
    page = client.get("/projects", headers={"Accept-Encoding": "gzip"})
    assert page.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in page.headers["Vary"]

    css = client.get("/static/css/style.css", headers={"Accept-Encoding": "gzip"})
    assert css.headers["Content-Encoding"] == "gzip"
    assert int(css.headers["Content-Length"]) < 20_000


def test_compression_is_skipped_when_it_would_not_help(client):
    """No gzip for clients that did not ask, or for already-compressed
    formats where a second pass only adds bytes."""
    plain = client.get("/projects", headers={"Accept-Encoding": "identity"})
    assert "Content-Encoding" not in plain.headers

    image = client.get("/static/images/profile.webp",
                       headers={"Accept-Encoding": "gzip"})
    assert "Content-Encoding" not in image.headers


def test_chart_gridlines_match_the_plot_geometry():
    """The reference lines are derived, not hardcoded.

    They were once written into the template by hand and drifted: the
    50% line sat six units away from where the data placed 50%, so every
    point rendered above a line labelled 50%.
    """
    lines = {g["label"]: g["y"] for g in pages.chart_gridlines()}
    points = pages.chart_points([
        {"gpa": 3.0, "rate": 100, "n": 1},
        {"gpa": 4.0, "rate": 50, "n": 1},
    ])
    assert lines["100%"] == points[0]["y"]
    assert lines["50%"] == points[1]["y"]
    assert lines["0%"] == pages.CHART_H - pages.CHART_PAD_B


# ------------------------------------------------------ loader failure paths

@pytest.mark.parametrize("loader,attr,fallback", [
    (pages.load_projects, "DATA_FILE", []),
    (pages.load_stats, "STATS_FILE", None),
    (pages.load_skills, "SKILLS_FILE", []),
    (pages.load_data_sources, "SKILLS_FILE", set()),
])
def test_loaders_return_a_fallback_when_the_file_is_missing(
        monkeypatch, tmp_path, loader, attr, fallback):
    """A missing data file degrades to empty rather than raising."""
    monkeypatch.setattr(pages, attr, tmp_path / "absent.json")
    assert loader() == fallback


@pytest.mark.parametrize("loader,attr,fallback", [
    (pages.load_projects, "DATA_FILE", []),
    (pages.load_stats, "STATS_FILE", None),
    (pages.load_skills, "SKILLS_FILE", []),
    (pages.load_data_sources, "SKILLS_FILE", set()),
])
def test_loaders_return_a_fallback_on_malformed_json(
        monkeypatch, tmp_path, loader, attr, fallback):
    """Truncated or corrupt JSON is caught, not propagated."""
    broken = tmp_path / "broken.json"
    broken.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(pages, attr, broken)
    assert loader() == fallback


@pytest.mark.parametrize("payload", [
    ["not", "a", "mapping"],
    {"records": 1},
    {"records": 1, "universities": 1, "programs": 1,
     "gpa_curve": [{"gpa": 3.0, "rate": 50}]},   # entry missing n
])
def test_structurally_incomplete_stats_are_rejected(monkeypatch, tmp_path, payload):
    """Valid JSON of the wrong shape is treated as absent.

    This is the failure a half-finished build_stats.py run produces, and
    it used to reach the view and raise rather than being caught here.
    """
    path = tmp_path / "stats.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(pages, "STATS_FILE", path)
    assert pages.load_stats() is None


# ------------------------------------------------------------- work grouping

def _write_projects(tmp_path, monkeypatch, payload):
    """Point the project loader at a hand-written data file."""
    path = tmp_path / "projects.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(pages, "DATA_FILE", path)
    return path


def test_entries_default_to_coursework(modules):
    """The course modules carry no kind and are treated as coursework."""
    assert modules, "expected entries"
    assert {m["kind"] for m in modules} == {pages.DEFAULT_KIND}


def test_original_work_sorts_above_coursework(tmp_path, monkeypatch):
    """A project entry leads, whatever its position in the file.

    This is the whole point of the field: original work is what a reader
    cannot assume was scaffolded by an assignment, so it should not sit
    below thirteen assignments because it was added last.
    """
    _write_projects(tmp_path, monkeypatch, {"modules": [
        {"id": 1, "title": "Course one"},
        {"id": 2, "title": "Course two"},
        {"id": 100, "title": "Mine", "kind": "project"},
    ]})
    assert [m["title"] for m in pages.load_projects()] == [
        "Mine", "Course one", "Course two"]


def test_file_order_is_kept_within_a_group(tmp_path, monkeypatch):
    """Sorting is stable, so the file still decides sequence."""
    _write_projects(tmp_path, monkeypatch, {"modules": [
        {"id": 3, "title": "third"},
        {"id": 1, "title": "first"},
        {"id": 2, "title": "second"},
    ]})
    assert [m["title"] for m in pages.load_projects()] == [
        "third", "first", "second"]


def test_ghost_numeral_defaults_to_the_padded_id(modules):
    """Every entry gets the numeral the template draws behind it."""
    assert all(m["num"] == f"{m['id']:02d}" for m in modules)


@pytest.mark.parametrize("entry,expected", [
    ({"id": 7}, "07"),
    ({"id": 7, "num": "A"}, "A"),
    ({"id": "nine"}, ""),
    ({}, "00"),
])
def test_ghost_numeral_rules(tmp_path, monkeypatch, entry, expected):
    """An explicit num wins; an unusable id yields no numeral, not a crash."""
    _write_projects(tmp_path, monkeypatch, {"modules": [entry]})
    assert pages.load_projects()[0]["num"] == expected


@pytest.mark.parametrize("payload", [
    ["not", "a", "mapping"],
    {"modules": "not a list"},
])
def test_malformed_project_data_yields_no_entries(tmp_path, monkeypatch, payload):
    """Valid JSON of the wrong shape empties the list instead of raising."""
    _write_projects(tmp_path, monkeypatch, payload)
    assert not pages.load_projects()


def test_non_object_entries_are_skipped(tmp_path, monkeypatch):
    """One bad entry drops itself, not the entries around it."""
    _write_projects(tmp_path, monkeypatch, {"modules": [
        {"id": 1, "title": "kept"}, "junk", {"id": 2, "title": "also kept"},
    ]})
    assert [m["title"] for m in pages.load_projects()] == ["kept", "also kept"]


@pytest.mark.parametrize("payload", [
    {"modules": []},                    # no sections key at all
    {"sections": [], "modules": []},    # present but empty
    {"sections": "nonsense", "modules": []},
])
def test_sections_fall_back_when_absent_or_unusable(
        tmp_path, monkeypatch, payload):
    """Removing the headings block cannot take the page down."""
    _write_projects(tmp_path, monkeypatch, payload)
    assert pages.load_sections() == pages.FALLBACK_SECTIONS


def test_sections_without_a_key_are_dropped(tmp_path, monkeypatch):
    """A heading that names no group cannot match one, so it is discarded."""
    _write_projects(tmp_path, monkeypatch, {"sections": [
        {"key": "project", "label": "Selected work"},
        {"label": "Orphan"},
    ], "modules": []})
    assert [s["label"] for s in pages.load_sections()] == ["Selected work"]


def test_empty_groups_are_not_rendered():
    """A section with no entries produces no heading."""
    sections = [{"key": "project", "label": "Selected work"},
                {"key": "coursework", "label": "Coursework"}]
    groups = pages.group_projects(
        [{"kind": "coursework", "title": "one"}], sections)
    assert [g["key"] for g in groups] == ["coursework"]
    assert [m["title"] for m in groups[0]["items"]] == ["one"]


def test_headings_appear_only_once_a_second_kind_exists(client, tmp_path,
                                                        monkeypatch):
    """The list stays ungrouped until there is something to group.

    The thirteen course entries should look exactly as they did before
    grouping existed; adding one original project is what introduces the
    headings.
    """
    one_kind = {"sections": [{"key": "coursework", "label": "Coursework"}],
                "modules": [{"id": 1, "title": "Course", "tags": [],
                             "area_key": "prod", "images": []}]}
    _write_projects(tmp_path, monkeypatch, one_kind)
    assert b"section-head" not in client.get("/projects").data

    both = json.loads(json.dumps(one_kind))
    both["sections"].insert(0, {"key": "project", "label": "Selected work",
                                "blurb": "Work of my own."})
    both["modules"].append({"id": 100, "title": "Mine", "kind": "project",
                            "tags": [], "area_key": "ml", "images": []})
    _write_projects(tmp_path, monkeypatch, both)
    page = client.get("/projects").data
    assert b"section-head" in page
    assert b"Selected work" in page and b"Work of my own." in page
    assert page.index(b"Selected work") < page.index(b"Coursework")


# ------------------------------------------------------- minified siblings

def test_the_minified_stylesheet_is_the_one_served(client):
    """Visitors get the compact copy, not the annotated source."""
    page = client.get("/").data.decode()
    assert "css/style.min.css" in page
    assert "css/style.css?" not in page


def test_a_stale_minified_sibling_is_ignored(tmp_path, monkeypatch):
    """Editing a source without rebuilding costs bytes, not correctness.

    A sibling older than its source was built from code that no longer
    exists. Serving it would ship the previous stylesheet, which is the
    silent-wrong-answer failure the mtime stamp exists to prevent, so the
    readable source is served instead.
    """
    static = tmp_path / "static"
    (static / "css").mkdir(parents=True)
    source = static / "css" / "style.css"
    minified = static / "css" / "style.min.css"
    minified.write_text("a{}", encoding="utf-8")
    source.write_text("a { }", encoding="utf-8")
    os.utime(minified, (1, 1))          # older than the source

    app = create_app()
    app.config.update(TESTING=True)
    monkeypatch.setattr(app, "static_folder", str(static))
    with app.test_request_context():
        assert "style.min.css" not in app.jinja_env.globals["asset"]("css/style.css")

    os.utime(minified, (10 ** 10, 10 ** 10))   # now newer
    app2 = create_app()
    monkeypatch.setattr(app2, "static_folder", str(static))
    with app2.test_request_context():
        assert "style.min.css" in app2.jinja_env.globals["asset"]("css/style.css")


def test_only_css_and_js_look_for_a_minified_sibling(client):
    """An image is served as itself; there is nothing to minify."""
    page = client.get("/").data.decode()
    assert "images/profile.webp" in page
    assert "profile.min.webp" not in page


# ------------------------------------------------------------ cache headers

def test_a_stamped_asset_is_cached_for_a_year(client):
    """A stamped URL names one revision, so it never needs revalidating."""
    stamped = re.search(r'href="([^"]*style\.min\.css\?v=\d+)"',
                        client.get("/").data.decode())
    assert stamped, "expected a stamped stylesheet URL"
    headers = client.get(stamped.group(1)).headers
    assert "max-age=31536000" in headers["Cache-Control"]
    assert "immutable" in headers["Cache-Control"]


def test_fonts_are_cached_for_a_year(client):
    """A font filename names one exact face, so it never changes under us."""
    headers = client.get(
        "/static/fonts/inter-latin-400-normal.woff2").headers
    assert "max-age=31536000" in headers["Cache-Control"]
    assert "immutable" in headers["Cache-Control"]


def test_an_unstamped_asset_is_revalidated(client):
    """An unstamped path names whatever is there today, so it expires."""
    headers = client.get("/static/images/profile.webp").headers
    assert "max-age=86400" in headers["Cache-Control"]
    assert "must-revalidate" in headers["Cache-Control"]


def test_pages_are_not_given_static_cache_headers(client):
    """The rule applies to the static endpoint, not to rendered pages."""
    assert "immutable" not in client.get("/").headers.get("Cache-Control", "")


def test_a_case_page_links_public_source_when_there_is_some(client, modules):
    """The case page makes the same call as the projects page.

    Both read the one ``source`` key, so a project cannot advertise its code
    in the list and hide it on its own page.
    """
    with_source = [m for m in modules if m.get("case") and m.get("source")]
    assert with_source, "expected a case study with a public source"
    for module in with_source:
        page = client.get(f"/projects/{module['id']}").data.decode()
        assert module["source"]["url"] in page
        assert "Request the source" not in page


def test_a_case_page_without_source_offers_a_way_to_ask(client, modules):
    """Absent public source, the page gives the reader something to do."""
    without = [m for m in modules if m.get("case") and not m.get("source")]
    for module in without:
        page = client.get(f"/projects/{module['id']}").data.decode()
        assert "Request the source" in page
