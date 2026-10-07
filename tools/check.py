#!/usr/bin/env python3
"""Checks the static site: internal links/anchors resolve, tags balance, ids are unique,
images have alt, each page has lang/title/description. Usage: python3 tools/check.py"""
import os, sys
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = "/calendo-site/"
SVG = {"path","circle","rect","line","polyline","polygon","ellipse","use","stop"}
VOID = {"area","base","br","col","embed","hr","img","input","link","meta","source","track","wbr"}

class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.stack, s.ids, s.links, s.errors = [], [], [], []
        s.has = {"lang": False, "title": False, "desc": False}
    def handle_starttag(s, tag, attrs):
        a = dict(attrs)
        if tag == "html" and a.get("lang"): s.has["lang"] = True
        if tag == "title": s.has["title"] = True
        if tag == "meta" and a.get("name") == "description" and a.get("content"): s.has["desc"] = True
        if "id" in a: s.ids.append(a["id"])
        for k in ("href", "src", "srcset"):
            if k in a: s.links.append((tag, a[k].split()[0]))
        if tag == "img" and "alt" not in a: s.errors.append(f"img without alt: {a.get('src')}")
        if tag not in VOID: s.stack.append((tag, s.getpos()))
    def handle_startendtag(s, tag, attrs):
        if tag not in VOID and tag not in SVG: s.errors.append(f"self-closing non-void <{tag}/>")
        s.handle_starttag(tag, attrs); 
        if tag not in VOID: s.stack.pop()
    def handle_endtag(s, tag):
        if tag in VOID: return
        if not s.stack: s.errors.append(f"stray </{tag}> at {s.getpos()}"); return
        t, pos = s.stack.pop()
        if t != tag: s.errors.append(f"</{tag}> at {s.getpos()} closes <{t}> from {pos}")

pages = {}
for d, _, fs in os.walk(ROOT):
    if "/.git" in d or d.endswith("/tools"): continue
    for f in fs:
        if f.endswith(".html"):
            path = os.path.join(d, f); p = P(); p.feed(open(path, encoding="utf-8").read()); p.close()
            pages[path] = p

def resolve(page, url):
    u = urlparse(url)
    if u.scheme in ("http", "https", "mailto", "tel") or url.startswith("data:"): return None, None
    if u.path.startswith("/"):
        if not u.path.startswith(PREFIX): return "BAD", u.fragment
        target = os.path.join(ROOT, unquote(u.path[len(PREFIX):]))
    elif u.path == "":
        target = page
    else:
        target = os.path.normpath(os.path.join(os.path.dirname(page), unquote(u.path)))
    if os.path.isdir(target) or target.endswith("/"): target = os.path.join(target, "index.html")
    return target, u.fragment

bad = 0
for path, p in pages.items():
    rp = os.path.relpath(path, ROOT)
    for e in p.errors: print(f"{rp}: {e}"); bad += 1
    for t, pos in p.stack: print(f"{rp}: unclosed <{t}> from {pos}"); bad += 1
    dup = {i for i in p.ids if p.ids.count(i) > 1}
    if dup: print(f"{rp}: duplicate ids {dup}"); bad += 1
    for k, v in p.has.items():
        if not v and not rp.startswith("404"): print(f"{rp}: missing {k}"); bad += 1
    for tag, url in p.links:
        if url == "#": continue  # App Store placeholder
        target, frag = resolve(path, url)
        if target is None: continue
        if target == "BAD" or not os.path.exists(target): print(f"{rp}: broken link {url}"); bad += 1; continue
        if frag and target in pages and frag not in pages[target].ids: print(f"{rp}: missing anchor {url}"); bad += 1
print(f"{len(pages)} pages checked, {bad} problem(s)")
sys.exit(1 if bad else 0)
