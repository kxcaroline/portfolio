# Adding a project

Everything the projects page renders comes from
`flask_website/data/projects.json`. Adding work is an edit to that file and
some images — no template or Python change.

## The short version

1. Append an entry to `modules` (template below).
2. Put screenshots in `flask_website/static/images/projects/<slug>/`.
3. Run `python build_thumbs.py`.
4. Fill in `image_dims` from what that prints, or leave `images` empty.
5. `pytest` — the suite checks the entry against the files on disk.

## Two kinds of entry

Each entry carries a `kind`:

- `"project"` — original work, not coursework. Renders under **Selected
  work**, above everything else.
- `"coursework"` — the default. An entry with no `kind` is coursework, which
  is why the thirteen course modules carry no such field.

Section headings appear only once both kinds are present. While the file
holds coursework alone the page reads as one ungrouped list, exactly as it
did before grouping existed.

## Entry template

```json
{
  "id": 100,
  "code": "P01",
  "num": "01",
  "kind": "project",
  "title": "What it is, in five or six words",
  "date": "Sep 2026",
  "area_key": "ml",
  "area": "ML & Modeling",
  "tags": ["Python", "PyTorch", "DuckDB"],
  "overview": "What it does and what it found. Two or three sentences, written for someone deciding whether to click.",
  "learned": "The one thing you would tell another engineer about it.",
  "source": {
    "label": "Read the source",
    "url": "https://github.com/kxcaroline/<repo>"
  },
  "live": {
    "label": "Try it live",
    "url": "https://..."
  },
  "images": ["myproject/overview.webp"],
  "image_dims": [[1400, 900]],
  "image_labels": ["Overview"]
}
```

### Field notes

| Field | Notes |
|---|---|
| `id` | Routing key for the case-study URL, and must be unique. **Use 100 and up for original work** so it can never collide with a course module number. |
| `code` | The short badge beside the title. `M01`–`M13` are coursework; `P01`, `P02` … keeps original work visibly separate. |
| `num` | The large numeral drawn behind the block. Defaults to the zero-padded `id`, which would read `100`, so set it explicitly. |
| `area_key` | One of `data`, `ml`, `prod` — it colours the block. |
| `area` | The label shown at the right of the title row. Keep it under about 95px rendered, or it crosses into the body column; the three current labels are 91–112px. |
| `source` | Omit it and the entry shows "Private repo" instead of a link. |
| `live` | Optional. Opens in a new tab. |
| `embed` | Optional. Loads an iframe on click; see the M13 entry for the shape, including its `caveat` line. |
| `case` | Optional. Its presence creates a page at `/projects/<id>`; see M10 or M13 for the structure. |
| `images` | At most three are shown in the strip. Paths are relative to `static/images/projects/`. |
| `image_dims` | The real pixel size of each image. A test asserts these match the files, because wrong values reintroduce layout shift that looks correct on screen. |

## When you add the first original project

Two lines of copy stop being true the moment the list is no longer all
coursework. Both live in `projects.json`, not in a template:

- The page intro in `templates/projects.html` still reads "Thirteen projects
  from Modern Software Concepts in Python." Move that sentence into the
  `coursework` section's `blurb` and give the page a broader intro.
- Give the `project` section a `blurb` — one line saying what this group is.

## Images

`build_thumbs.py` writes a 344px WebP copy of every screenshot into
`static/images/thumbs/`, mirroring the folder layout, and records each
thumbnail's size in `data/thumb_sizes.json`. The page serves the thumbnail
and fetches the full capture only when the lightbox opens, so a large source
image costs nothing until someone asks for it.

Screenshots should not include browser chrome — no title bars, no traffic
lights. Crop to the content.
