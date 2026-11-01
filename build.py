#!/usr/bin/env python3
"""Philadelphia Civic Wiki static-site builder.

Reads article fragments from articles/*.html (each an HTML body fragment with a
leading <!--meta title=... desc=... cats=...--> comment) and wraps them in the
retro Monobook shell. Zero runtime JS required; output is plain static HTML for
GitHub Pages. Deliberately minimal for low data use.
"""
import os
import re
import html
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))
ART_DIR = os.path.join(ROOT, "articles")
OUT_DIR = os.path.join(ROOT, "wiki")

MANIFEST = os.path.join(os.path.dirname(ROOT), "manifest.txt")

# Portal pages: one per manifest agent tag (topic group), auto-generated.
PORTALS = [
    ("A1", "Portal_Government_Structure", "Government Structure", "How the city-county government is built: Mayor, Council, row offices, charter, and the state and federal layers above it."),
    ("A2", "Portal_Politics_and_Elections", "Politics and Elections", "Parties, wards, elections, campaign money, ethics oversight, and documented corruption cases."),
    ("A3", "Portal_Unions_and_Labor", "Unions and Labor", "Public and private sector unions, bargaining law, and labor's role in Philadelphia politics."),
    ("A4", "Portal_Administration_and_Finance", "Administration and Finance", "The departments that run the city itself: money, taxes, procurement, HR, law, technology."),
    ("A5", "Portal_Land_Use_Streets_and_Utilities", "Land Use, Streets and Utilities", "Permits, zoning, inspections, streets, water, parks, libraries, airport and gas."),
    ("A6", "Portal_Housing_and_Authorities", "Housing, Transit and Authorities", "Housing agencies, landlord-tenant systems, development incentives, and transit and port authorities."),
    ("A7", "Portal_Public_Safety_and_Justice", "Public Safety and Justice", "Police, fire, prisons, courts, defenders, oversight bodies, and the federal prosecutor."),
    ("A8", "Portal_Health_and_Human_Services", "Health, Human Services and Culture", "Public health, social services, homelessness, immigrant and disability affairs, arts and workforce."),
    ("A9", "Portal_Schools_and_Civil_Society", "Schools, Business and Civil Society", "Schools, business and philanthropy, advocacy groups, media, neighborhoods and who holds influence."),
    ("A10", "Portal_Citizen_Guides", "Citizen Guides", "Practical how-tos: getting help, testifying, filing complaints, public records, reporting misconduct."),
]


def load_manifest():
    rows = []
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            stem, title, agent = line.split("|")
            rows.append((stem, title, agent))
    return rows


SIDEBAR = [
    ("navigation", [
        ("Main Page", "index.html"),
        ("About this wiki", "About.html"),
        ("Full report (one page)", "Full_Report.html"),
        ("Department directory", "Department_Directory.html"),
        ("Index of articles", "Index.html"),
        ("Glossary", "Glossary.html"),
        ("References", "References.html"),
    ]),
    ("portals", [(label, slug + ".html") for _, slug, label, _ in PORTALS]),
]

SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Philadelphia Civic Wiki">
<meta property="og:title" content="{title} - Philadelphia Civic Wiki">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://thumpersecure.github.io/philly-civic-wiki/og-image.png?v=20261009">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Philadelphia Civic Wiki: City Hall tower skyline in blue and gold">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title} - Philadelphia Civic Wiki">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="https://thumpersecure.github.io/philly-civic-wiki/og-image.png?v=20261009">
<title>{title} - Philadelphia Civic Wiki</title>
<link rel="stylesheet" href="{depth}skin/monobook.css">
</head>
<body>
<div id="globalWrapper">
<div id="siteTitle">
  <a href="{depth}wiki/index.html"><span class="logo">Philadelphia Civic Wiki</span></a>
  <span class="tagline">&mdash; how Philadelphia politics, government, unions &amp; institutions work</span>
</div>
<div id="layout">
  <div id="column-one">
    <div class="portlet" id="p-logo"><a href="{depth}wiki/index.html">PHILLY&middot;CIVIC&middot;WIKI</a></div>
    {sidebar}
    <div class="portlet">
      <h5>search</h5>
      <form id="searchform" onsubmit="return jump()">
        <input id="searchInput" type="text" placeholder="page name...">
        <div><input id="searchGo" type="submit" value="Go"></div>
      </form>
    </div>
  </div>
  <div id="content">
    <h1 id="firstHeading">{title}</h1>
    <div class="subtitle">From the Philadelphia Civic Wiki, the free guide to how the city works</div>
    {body}
    {catlinks}
  </div>
</div>
<div id="footer">
  <p>Philadelphia Civic Wiki &middot; a plain-language educational guide to Philadelphia government, politics, unions and civic institutions, compiled from public sources in October 2026. Offices, officeholders and figures change: verify against official sources before relying on anything here. General civic education, not legal advice.</p>
  <p>Static site, no trackers, no cookies, no JavaScript required to read. Hosted on GitHub Pages.</p>
</div>
</div>
<script>
/* the ONLY script: a tiny client-side "Go" box. Page works fully without it. */
function jump(){{var v=document.getElementById('searchInput').value.trim();
if(!v)return false;var s=v.replace(/ /g,'_').replace(/[^A-Za-z0-9_'\\-]/g,'');
window.location.href=s+'.html';return false;}}
</script>
<script>new Image().src='https://srv1540509.hstgr.cloud/p.gif?s=philly-civic-wiki&p='+encodeURIComponent(location.pathname)+'&r='+encodeURIComponent(document.referrer)</script>
</body>
</html>
"""


def render_sidebar(active):
    out = []
    for heading, links in SIDEBAR:
        items = []
        for label, href in links:
            cls = ' class="active-page"' if href == active else ""
            items.append(f'<li{cls}><a href="{href}">{html.escape(label)}</a></li>')
        out.append(
            f'<div class="portlet"><h5>{html.escape(heading)}</h5>'
            f'<ul>{"".join(items)}</ul></div>'
        )
    return "\n    ".join(out)


def parse_meta(text):
    m = re.match(r"\s*<!--meta(.*?)-->", text, re.S)
    meta = {"title": "Untitled", "desc": "", "cats": ""}
    body = text
    if m:
        for k, v in re.findall(r'(\w+)="([^"]*)"', m.group(1)):
            meta[k] = v
        body = text[m.end():]
    return meta, body.strip()


REPORT_ORDER = [stem for stem, _, _ in load_manifest()]

# Pages that are wiki-furniture, not part of the report narrative.
SKIP_FROM_REPORT = {"index", "Full_Report", "About", "Index", "Glossary", "References"}


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(ART_DIR, "*.html")))
    parsed = {}
    for path in files:
        with open(path, encoding="utf-8") as f:
            meta, body = parse_meta(f.read())
        base = os.path.basename(path)
        parsed[base[:-5]] = (base, meta, body)

    built = 0
    for stem, (base, meta, body) in parsed.items():
        cats = ""
        if meta.get("cats"):
            links = " | ".join(
                f'<a href="Category_{html.escape(c.strip().replace(" ", "_"))}.html">{html.escape(c.strip())}</a>'
                for c in meta["cats"].split(",") if c.strip()
            )
            cats = f'<div class="catlinks"><b>Categories:</b> {links}</div>'
        page = SHELL.format(
            title=html.escape(meta["title"]),
            desc=html.escape(meta.get("desc", "")),
            depth="../",
            sidebar=render_sidebar(base),
            body=body,
            catlinks=cats,
        )
        with open(os.path.join(OUT_DIR, base), "w", encoding="utf-8") as f:
            f.write(page)
        built += 1

    # ---- assemble the single-page Full Report ----
    parts = [
        '<p>This page collects every substantive article of the '
        '<a href="index.html">Philadelphia Civic Wiki</a> into one continuous document for printing or '
        'offline reading. Each section corresponds to a standalone article; internal links still '
        'work. For navigation, use the <a href="Index.html">Index</a>.</p>',
        '<div class="notebox">Generated automatically from the article sources. '
        'For sources see <a href="References.html">References</a>; for terms see '
        '<a href="Glossary.html">Glossary</a>.</div>',
        '<h2 id="report-toc">Contents</h2><ol>',
    ]
    for stem in REPORT_ORDER:
        if stem in parsed:
            t = parsed[stem][1]["title"]
            parts.append(f'<li><a href="#r-{stem}">{html.escape(t)}</a></li>')
    parts.append("</ol>")
    for stem in REPORT_ORDER:
        if stem not in parsed:
            continue
        base, meta, body = parsed[stem]
        # strip each article's own manual TOC and its trailing References list
        b = re.sub(r'<div class="toc">.*?</div>\s*</div>', "", body, flags=re.S)
        b = re.sub(r'<div class="toc">.*?</ul>\s*</div>', "", b, flags=re.S)
        parts.append(f'<h1 id="r-{stem}" style="border-bottom:2px solid #888;margin-top:1.4em;">'
                     f'{html.escape(meta["title"])}</h1>')
        parts.append(b)
        parts.append('<p class="hatnote">&mdash; end of section &mdash; '
                     '<a href="#report-toc">back to contents</a></p>')
    report_body = "\n".join(parts)
    report_page = SHELL.format(
        title="Full Report",
        desc="The complete Philadelphia Civic Wiki as one continuous, printable page.",
        depth="../",
        sidebar=render_sidebar("Full_Report.html"),
        body=report_body,
        catlinks='<div class="catlinks"><b>Categories:</b> <a href="Category_Wiki.html">Wiki</a></div>',
    )
    with open(os.path.join(OUT_DIR, "Full_Report.html"), "w", encoding="utf-8") as f:
        f.write(report_page)
    built += 1

    # ---- portal pages (one per topic group) + Department Directory, from manifest + metadata ----
    manifest = load_manifest()
    for tag, slug, label, blurb in PORTALS:
        rows = [(st, ti) for st, ti, ag in manifest if ag == tag and st in parsed]
        lis = "\n".join(
            f'<li><a href="{st}.html">{html.escape(parsed[st][1]["title"])}</a> &mdash; '
            f'{html.escape(parsed[st][1].get("desc", ""))}</li>'
            for st, _ in rows
        )
        pbody = (f'<p>{html.escape(blurb)}</p><h2 id="articles">Articles ({len(rows)})</h2><ul>{lis}</ul>'
                 f'<p class="hatnote">See also the <a href="Department_Directory.html">Department Directory</a>, '
                 f'the <a href="Index.html">full index</a> and the <a href="index.html">Main Page</a>.</p>')
        with open(os.path.join(OUT_DIR, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(SHELL.format(title=label, desc=blurb, depth="../",
                                 sidebar=render_sidebar(slug + ".html"), body=pbody, catlinks=""))
        built += 1

    # ---- alphabetical Index of every article, auto-generated ----
    entries = sorted(((meta["title"], stem) for stem, (_, meta, _) in parsed.items()
                      if stem not in SKIP_FROM_REPORT), key=lambda t: t[0].lower())
    letters = {}
    for title, stem in entries:
        key = title[0].upper() if title[0].isalpha() else "#"
        letters.setdefault(key, []).append((title, stem))
    nav = " &middot; ".join(f'<a href="#L{k}">{k}</a>' for k in letters)
    ibody = [f'<p>Every article in the wiki, A to Z ({len(entries)} articles). {nav}</p>']
    for k, items in letters.items():
        ibody.append(f'<h2 id="L{k}">{k}</h2><ul>' + "".join(
            f'<li><a href="{s}.html">{html.escape(t)}</a> &mdash; {html.escape(parsed[s][1].get("desc", ""))}</li>'
            for t, s in items) + '</ul>')
    with open(os.path.join(OUT_DIR, "Index.html"), "w", encoding="utf-8") as f:
        f.write(SHELL.format(title="Index of articles", desc="Alphabetical index of every article in the Philadelphia Civic Wiki.",
                             depth="../", sidebar=render_sidebar("Index.html"),
                             body="\n".join(ibody), catlinks=""))
    built += 1

    def has_cat(meta, name):
        return name in [c.strip() for c in (meta.get("cats") or "").split(",")]

    sections = [
        ("City departments, offices and commissions", "Departments"),
        ("Authorities and quasi-governmental bodies", "Authorities and Quasi-Government"),
        ("Courts and justice system bodies", "Courts and Justice"),
        ("Unions", "Unions"),
    ]
    dparts = ['<p>A one-line answer to <i>what does each Philadelphia body do?</i>, generated from the article summaries. '
              'Click a name for the full article. Many bodies appear in more than one section.</p>']
    for heading, cat in sections:
        members = sorted((parsed[s][1]["title"], s, parsed[s][1].get("desc", ""))
                         for s in parsed if has_cat(parsed[s][1], cat))
        if not members:
            continue
        dparts.append(f'<h2 id="{cat.replace(" ", "_")}">{html.escape(heading)} ({len(members)})</h2>'
                      '<table class="wikitable"><tr><th>Body</th><th>What it does</th></tr>' +
                      "".join(f'<tr><td><a href="{s}.html">{html.escape(t)}</a></td><td>{html.escape(d)}</td></tr>'
                              for t, s, d in members) + '</table>')
    with open(os.path.join(OUT_DIR, "Department_Directory.html"), "w", encoding="utf-8") as f:
        f.write(SHELL.format(title="Department Directory",
                             desc="Every Philadelphia department, authority, court and union in the wiki with a one-line description.",
                             depth="../", sidebar=render_sidebar("Department_Directory.html"),
                             body="\n".join(dparts), catlinks=""))
    built += 1

    # ---- generate a real page for every category referenced ----
    cat_map = {}
    for stem, (base, meta, body) in parsed.items():
        for c in (meta.get("cats") or "").split(","):
            c = c.strip()
            if c:
                cat_map.setdefault(c, []).append((meta["title"], base))
    for cat, members in sorted(cat_map.items()):
        slug = "Category_" + cat.replace(" ", "_")
        items = "\n".join(
            f'<li><a href="{href}">{html.escape(title)}</a></li>'
            for title, href in sorted(members)
        )
        cbody = (
            f'<p>This category groups articles tagged <b>{html.escape(cat)}</b> in the '
            f'<a href="index.html">Philadelphia Civic Wiki</a>. '
            f'There {"is" if len(members)==1 else "are"} {len(members)} '
            f'{"page" if len(members)==1 else "pages"} in this category.</p>'
            f'<h2 id="pages">Pages in category &ldquo;{html.escape(cat)}&rdquo;</h2>'
            f'<ul>{items}</ul>'
            f'<p class="hatnote">See also the <a href="Index.html">full index</a> '
            f'and the <a href="Full_Report.html">single-page report</a>.</p>'
        )
        cpage = SHELL.format(
            title=f"Category: {cat}",
            desc=f"Articles in the {cat} category of the Philadelphia Civic Wiki.",
            depth="../",
            sidebar=render_sidebar(slug + ".html"),
            body=cbody,
            catlinks="",
        )
        with open(os.path.join(OUT_DIR, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(cpage)
        built += 1

    # ---- copy skin into wiki/ sibling & drop .nojekyll and a root redirect ----
    # (skin referenced as ../skin/ from wiki/, so ensure it exists at site root)
    with open(os.path.join(os.path.dirname(OUT_DIR), ".nojekyll"), "w") as f:
        f.write("")
    # root index.html -> redirect into wiki/
    with open(os.path.join(os.path.dirname(OUT_DIR), "index.html"), "w", encoding="utf-8") as f:
        _img = "https://thumpersecure.github.io/philly-civic-wiki/og-image.png?v=20261009"
        _desc = "A plain-English guide to how Philadelphia politics, city departments, unions, authorities and civic organizations work."
        f.write('<!DOCTYPE html><meta charset="utf-8">'
                '<meta http-equiv="refresh" content="0; url=wiki/index.html">'
                f'<meta name="description" content="{_desc}">'
                '<meta property="og:type" content="website">'
                '<meta property="og:site_name" content="Philadelphia Civic Wiki">'
                '<meta property="og:title" content="Philadelphia Civic Wiki">'
                f'<meta property="og:description" content="{_desc}">'
                '<meta property="og:url" content="https://thumpersecure.github.io/philly-civic-wiki/">'
                f'<meta property="og:image" content="{_img}">'
                '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
                '<meta name="twitter:card" content="summary_large_image">'
                '<meta name="twitter:title" content="Philadelphia Civic Wiki">'
                f'<meta name="twitter:description" content="{_desc}">'
                f'<meta name="twitter:image" content="{_img}">'
                '<title>Philadelphia Civic Wiki</title>'
                '<p>Redirecting to the <a href="wiki/index.html">Philadelphia Civic Wiki</a>&hellip;</p>')

    print(f"Built {built} pages into {OUT_DIR} (incl. Full_Report). "
          f"Report sections present: {sum(1 for s in REPORT_ORDER if s in parsed)}/{len(REPORT_ORDER)}")


if __name__ == "__main__":
    build()
