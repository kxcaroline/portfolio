"""Page routes: home, projects, case studies, contact.

Every page is data-driven. Project entries, the aggregate dataset figures
and the featured-skill list all live in flask_website/data/*.json and are
loaded here, so adding work is an edit to a data file rather than to a
template. Each loader degrades to an empty result rather than raising: a
half-written data file should drop one section, not take the site down.
"""

import json
from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, send_from_directory

# Create the blueprint. "pages" is the name used by url_for().
bp = Blueprint("pages", __name__)

# Path to the JSON data file, relative to this file so it works no matter
# where the app is launched from.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE = DATA_DIR / "projects.json"
STATS_FILE = DATA_DIR / "site_stats.json"
SKILLS_FILE = DATA_DIR / "skills.json"

# Plot geometry for the homepage figure (SVG user units).
CHART_W, CHART_H = 520, 150
CHART_PAD_L, CHART_PAD_R, CHART_PAD_T, CHART_PAD_B = 34, 12, 12, 24


# Entries are grouped by what kind of work they are, and the groups run in
# this order. Original work leads because it is the work a reader cannot
# assume was scaffolded by an assignment; coursework follows. An entry that
# names no kind is coursework, so the thirteen course modules needed no
# edit when this was introduced.
DEFAULT_KIND = "coursework"
KIND_ORDER = ("project", DEFAULT_KIND)

# Used when projects.json carries no "sections" key, so the page still has
# headings to render if that block is ever removed.
FALLBACK_SECTIONS = [
    {"key": "project", "label": "Selected work"},
    {"key": DEFAULT_KIND, "label": "Coursework"},
]


def _read_data():
    """Parsed projects.json, or an empty mapping if it cannot be read."""
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_projects():
    """Project entries from JSON, original work first.

    Each entry is returned with two derived keys the templates rely on:
    ``kind`` (defaulted) and ``num`` (the numeral drawn behind the block,
    which is the id zero-padded unless the entry sets its own). Deriving
    them here rather than in the template means a new entry needs neither
    field to render correctly.

    Returns an empty list if the file is missing or malformed, so the
    Projects page degrades gracefully instead of crashing.
    """
    modules = _read_data().get("modules", [])
    if not isinstance(modules, list):
        return []

    prepared = []
    for entry in modules:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        item["kind"] = item.get("kind") or DEFAULT_KIND
        if not item.get("num"):
            try:
                item["num"] = f"{int(item.get('id', 0)):02d}"
            except (TypeError, ValueError):
                item["num"] = ""
        prepared.append(item)

    # Stable sort: entries keep their order in the file within a group, so
    # the file stays the place where sequence is decided.
    rank = {kind: i for i, kind in enumerate(KIND_ORDER)}
    prepared.sort(key=lambda m: rank.get(m["kind"], len(rank)))
    return prepared


def load_sections():
    """Group headings, keyed by the ``kind`` they describe.

    Held in projects.json beside the entries themselves so the wording is
    content rather than markup, and read through a fallback so removing
    the block cannot take the page down.
    """
    sections = _read_data().get("sections")
    if not isinstance(sections, list) or not sections:
        return list(FALLBACK_SECTIONS)
    return [s for s in sections if isinstance(s, dict) and s.get("key")]


def group_projects(modules, sections):
    """Pair each section with its entries, dropping empty groups.

    A section with nothing in it is not rendered at all, which is what
    lets the page look unchanged until the first entry of a new kind is
    added.
    """
    groups = []
    for section in sections:
        items = [m for m in modules if m["kind"] == section["key"]]
        if items:
            groups.append({**section, "items": items})
    return groups


def load_stats():
    """Read the aggregate dataset figures shown on the home page.

    Produced by build_stats.py from the cleaned Grad Café dataset.
    Returns None if the file is absent, unreadable, or structurally
    incomplete, so the page omits the figure rather than failing: a
    half-written stats file should not take the Projects page down.
    """
    required = ("records", "universities", "programs", "gpa_curve")
    try:
        with open(STATS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or any(k not in data for k in required):
        return None
    if not all(isinstance(p, dict) and {"gpa", "rate", "n"} <= set(p)
               for p in data["gpa_curve"]):
        return None
    return data


# The order the focus areas are presented in, on the home page and
# anywhere else they are listed together.
AREA_ORDER = [
    ("prod", "Cloud & DevOps"),
    ("data", "Data Engineering"),
    ("ml", "ML & Modeling"),
]


def load_data_sources():
    """Tag names that identify a dataset rather than a tool.

    They are held apart so the "also worked with" line stays a list of
    things used, not a mix of tools and the places data came from.
    """
    try:
        with open(SKILLS_FILE, encoding="utf-8") as f:
            return set(json.load(f).get("data_sources", []))
    except (OSError, json.JSONDecodeError):
        return set()


def load_skills():
    """Read the curated list of featured skills.

    Featured skills are hand-picked (three per focus area) because
    "what I want to be judged on" is an editorial decision, not
    something that can be derived from tag counts.
    """
    try:
        with open(SKILLS_FILE, encoding="utf-8") as f:
            return json.load(f).get("featured", [])
    except (OSError, json.JSONDecodeError):
        return []


def build_skills(modules):
    """Featured skills grouped by focus area, plus everything else.

    The featured entries come from skills.json; the "also worked with"
    list is whatever remains in the project tags, so the site can never
    silently drop a technology that the projects actually use.
    """
    featured = load_skills()
    by_name: dict[str, dict[str, str]] = {}
    for mod in modules:
        for tag in mod.get("tags", []):
            by_name.setdefault(tag, {"name": tag})

    highlighted = {s["name"] for s in featured}
    groups = []
    for key, label in AREA_ORDER:
        items = []
        for skill in featured:
            if skill.get("area_key") != key:
                continue
            items.append(dict(skill))
        groups.append({"key": key, "label": label, "items": items})

    sources = load_data_sources()
    rest = sorted(
        (e for name, e in by_name.items()
         if name not in highlighted and name not in sources),
        key=lambda e: e["name"].lower(),
    )
    data_sources = sorted(
        (e for name, e in by_name.items() if name in sources),
        key=lambda e: e["name"].lower(),
    )
    return {"groups": groups, "rest": rest, "data_sources": data_sources}


# A screenshot is at most this many times taller than it is wide before the
# thumbnail stops trying to show the whole thing. Below it, fitting the whole
# image inside the tile keeps every screenshot legible; above it — full-page
# captures four thousand pixels tall — fitting produces an unreadable sliver,
# so the tile shows the top of the page instead, the way a page preview does.
THUMB_TALL_RATIO = 2.0


THUMB_SIZES_FILE = DATA_DIR / "thumb_sizes.json"


def load_thumb_sizes():
    """Pixel sizes of the generated thumbnails, keyed by image name.

    Written by build_thumbs.py alongside the images themselves, so the two
    cannot disagree, and read here rather than measured: opening 32 files to
    render a page would put an image library in the deployed application for
    information that is fixed the moment the thumbnails are built.
    """
    try:
        with open(THUMB_SIZES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


@bp.app_template_filter("thumb_size")
def thumb_size(name):
    """Size of one thumbnail, or None if it has not been generated.

    None makes the template omit the width and height attributes rather than
    declare wrong ones - absent attributes cost a layout shift, wrong ones
    cost a shift that looks correct.
    """
    return _THUMB_SIZES.get(name)


_THUMB_SIZES = load_thumb_sizes()


@bp.app_template_filter("thumb_class")
def thumb_class(dims):
    """CSS class for one screenshot thumbnail, chosen from its real size."""
    if not dims:
        return ""
    width, height = dims[0], dims[1]
    return "thumb-crop" if width and height > width * THUMB_TALL_RATIO else ""


def chart_gridlines():
    """Y positions for the 0 / 50 / 100% gridlines.

    Derived from the same padding constants as chart_points() so the
    reference lines cannot drift away from the data they label.
    """
    plot_h = CHART_H - CHART_PAD_T - CHART_PAD_B
    return [
        {"y": round(CHART_PAD_T + (1 - r / 100) * plot_h, 1), "label": f"{r}%"}
        for r in (100, 50, 0)
    ]


def chart_points(curve):
    """Project the GPA/acceptance-rate curve into SVG coordinates.

    The y-axis is fixed to 0–100% rather than auto-scaled: the point of
    the figure is that the line is *flat*, and auto-scaling a narrow
    range would exaggerate noise into a false trend.

    Returns a list of dicts with the original values plus x/y positions.
    """
    # Skip anything without both coordinates rather than indexing blindly.
    # load_stats() already validates the file, but this is the function
    # that would raise, and a figure is never worth taking the page down
    # for — the template omits it when no points come back.
    usable = [p for p in (curve or [])
              if isinstance(p, dict) and "gpa" in p and "rate" in p]
    if not usable:
        return []

    xs = [p["gpa"] for p in usable]
    x_min, x_max = min(xs), max(xs)
    span = (x_max - x_min) or 1
    plot_w = CHART_W - CHART_PAD_L - CHART_PAD_R
    plot_h = CHART_H - CHART_PAD_T - CHART_PAD_B

    points = []
    for p in usable:
        x = CHART_PAD_L + (p["gpa"] - x_min) / span * plot_w
        y = CHART_PAD_T + (1 - p["rate"] / 100) * plot_h
        points.append({**p, "x": round(x, 1), "y": round(y, 1)})
    return points


@bp.route("/")
def home():
    """Home page: name, position, bio, and the featured skills."""
    return render_template(
        "home.html",
        active="home",
        skills=build_skills(load_projects()),
    )


@bp.route("/projects")
def projects():
    """Projects page: one content block per course module, loaded from JSON.

    The dataset band above the list is rendered from site_stats.json by the
    _dataset.html partial. Eleven of the thirteen projects are built on the
    same 96,948 records, which is what makes most of the list read as one
    body of work rather than a set of unrelated assignments.
    """
    stats = load_stats()
    points = chart_points(stats.get("gpa_curve") if stats else None)
    modules = load_projects()
    return render_template(
        "projects.html",
        active="projects",
        modules=modules,
        groups=group_projects(modules, load_sections()),
        stats=stats,
        points=points,
        # The figure's own sample, not the site-wide record count: the curve
        # covers only rows that report a GPA in this band AND a decided
        # outcome, which is a little under half the cleaned dataset.
        curve_n=sum(p["n"] for p in points),
        chart_w=CHART_W,
        chart_h=CHART_H,
        chart_baseline=CHART_H - CHART_PAD_B,
        gridlines=chart_gridlines(),
    )


@bp.route("/projects/<int:module_id>")
def case(module_id):
    """Case-study page for one project.

    Only modules that carry a "case" entry in projects.json have a page;
    anything else returns 404 rather than rendering an empty shell.
    """
    modules = load_projects()
    index = {m["id"]: i for i, m in enumerate(modules)}
    if module_id not in index:
        abort(404)

    position = index[module_id]
    module = modules[position]
    if not module.get("case"):
        abort(404)

    # Neighbouring case studies, for the previous/next links.
    def neighbour(step):
        i = position + step
        while 0 <= i < len(modules):
            if modules[i].get("case"):
                return modules[i]
            i += step
        return None

    return render_template(
        "case.html",
        active="projects",
        m=module,
        prev_m=neighbour(-1),
        next_m=neighbour(1),
    )


@bp.route("/demos/trials")
def demo_trials():
    """The Module 10 immuno-oncology dashboard, served as a standalone page.

    The file is a self-contained Plotly export — the library is inlined, so
    it needs no build step and no network at render time. It is served from
    a clean URL rather than the raw /static path so the demo is linkable and
    can be shared on its own.
    """
    # static_folder is Optional in Flask's types because an app can turn
    # static serving off; this one never does.
    assert current_app.static_folder is not None
    return send_from_directory(
        Path(current_app.static_folder) / "demos",
        "io-pipeline-dashboard.html",
    )


@bp.route("/contact")
def contact():
    """Contact page: email and LinkedIn information."""
    return render_template("contact.html", active="contact")
