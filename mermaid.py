#!/usr/bin/env python3

"""
Pandoc filter to process code blocks with class "mermaid" into
mermaid-generated images.

Uses the local Mermaid CLI (mmdc) if it is installed, otherwise falls back to
the mermaid.ink web service.

Optional attributes on the code block:
    caption="..."   figure caption
    theme=default   mermaid theme (default, dark, forest, neutral)
    bg=white        background colour (png/pdf only)
    width=..        image width in pixels used for rendering (mmdc/png)
"""

import base64
import os
import shutil
import subprocess
import sys
import tempfile

import requests

from pandocfilters import toJSONFilter, Para, Plain, Image, get_filename4code, get_caption, get_extension, get_value

try:
    from pandocfilters import Figure
except ImportError:
    sys.stderr.write("pandocfilters version is lacking Figure support, captions for mermaid images will not be supported.\n")
    Figure = None


def render_local(mmdc, code, dest, filetype, theme, bg):
    """Render using the mermaid CLI, returns True on success."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "diagram.mmd")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)

        cmd = [mmdc, "-i", src, "-o", dest, "-t", theme, "-b", bg]
        if filetype == "png":
            cmd += ["-s", "3"]
        if filetype == "pdf":
            cmd += ["--pdfFit"]

        # mmdc drives headless chromium, which often needs --no-sandbox in CI/containers
        pconfig = os.path.join(tmp, "puppeteer.json")
        with open(pconfig, "w") as f:
            f.write('{"args": ["--no-sandbox"]}')
        cmd += ["-p", pconfig]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(f"mmdc failed: {result.stderr}\n")
            return False
    return True


def render_web(code, dest, filetype, theme, bg):
    """Render using mermaid.ink, returns True on success."""
    encoded = base64.urlsafe_b64encode(code.encode("utf-8")).decode("ascii")
    params = {"theme": theme}
    if filetype == "svg":
        url = f"https://mermaid.ink/svg/{encoded}"
    elif filetype == "pdf":
        url = f"https://mermaid.ink/pdf/{encoded}"
        params["fit"] = ""
    else:
        url = f"https://mermaid.ink/img/{encoded}"
        params["type"] = "png"
        params["scale"] = "3"
    if filetype != "svg":
        params["bgColor"] = bg

    response = requests.get(url, params=params, timeout=60)
    if response.status_code != 200:
        sys.stderr.write(f"mermaid.ink error {response.status_code}: {response.text[:500]}\n")
        return False
    with open(dest, "wb") as f:
        f.write(response.content)
    return True


def mermaid(key, value, format, _):
    if key == 'CodeBlock':
        [[ident, classes, keyvals], code] = value
        if "mermaid" in classes:
            caption, typef, keyvals = get_caption(keyvals)
            theme, keyvals = get_value(keyvals, u"theme", u"default")
            bg, keyvals = get_value(keyvals, u"bg", u"white")
            filetype = get_extension(format, "png", beamer="pdf", html="svg", latex="pdf")
            # include options in the hash so changing them regenerates the image
            dest = get_filename4code("mermaid", code + theme + bg, filetype)

            if not os.path.isfile(dest):
                mmdc = shutil.which("mmdc")
                ok = False
                if mmdc:
                    ok = render_local(mmdc, code, dest, filetype, theme, bg)
                    if ok:
                        sys.stderr.write(f'Created image {dest}\n')
                if not ok:
                    ok = render_web(code, dest, filetype, theme, bg)
                    if ok:
                        sys.stderr.write(f'Created image using mermaid.ink {dest}\n')
                if not ok:
                    if os.path.isfile(dest):
                        os.remove(dest)
                    sys.stderr.write("Error creating mermaid image\n")
                    sys.stderr.write(code)
                    sys.exit(1)

            if caption and Figure is not None:
                return Figure(["", [], []],
                              [None, [Para(caption)]],
                              [Plain([Image([ident, [], keyvals], caption, [dest, typef])])])

            return Para([Image([ident, [], keyvals], caption, [dest, typef])])


if __name__ == "__main__":
    toJSONFilter(mermaid)
