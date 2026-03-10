#!/usr/bin/env python3
"""
build.py — Vercel build helper.
Called by Vercel's buildCommand.
Assembles the public/ directory with:
  /               → main landing page (frontend/)
  /static/*       → main site assets
  /admin/*        → React admin SPA (from auth_app/frontend/dist/)
"""

import shutil
import subprocess
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
FRONTEND_SRC = os.path.join(ROOT, "frontend")
ADMIN_SRC = os.path.join(ROOT, "auth_app", "frontend")
ADMIN_DIST = os.path.join(ADMIN_SRC, "dist")

def main():
    # Clean
    if os.path.exists(PUBLIC):
        shutil.rmtree(PUBLIC)
    os.makedirs(PUBLIC, exist_ok=True)

    # 1. Build React admin app
    print("==> Building React admin frontend...")
    subprocess.run(["npm", "install"], cwd=ADMIN_SRC, check=True)
    subprocess.run(["npm", "run", "build"], cwd=ADMIN_SRC, check=True)

    # 2. Copy main landing page assets to public/static/
    print("==> Copying main site assets to public/static/...")
    static_dir = os.path.join(PUBLIC, "static")
    os.makedirs(static_dir, exist_ok=True)
    for f in os.listdir(FRONTEND_SRC):
        src = os.path.join(FRONTEND_SRC, f)
        dst = os.path.join(static_dir, f)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

    # 3. Copy main index.html to public/index.html
    print("==> Copying main index.html...")
    shutil.copy2(os.path.join(FRONTEND_SRC, "index.html"), os.path.join(PUBLIC, "index.html"))

    # 4. Copy React admin build to public/admin/
    print("==> Copying React admin build to public/admin/...")
    admin_out = os.path.join(PUBLIC, "admin")
    if os.path.exists(ADMIN_DIST):
        shutil.copytree(ADMIN_DIST, admin_out)
    else:
        print("WARNING: admin dist not found at", ADMIN_DIST)

    print("==> Build complete! public/ directory ready.")
    # List contents
    for dirpath, dirnames, filenames in os.walk(PUBLIC):
        level = dirpath.replace(PUBLIC, "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(dirpath)}/")
        sub_indent = " " * 2 * (level + 1)
        for f in filenames[:10]:
            print(f"{sub_indent}{f}")
        if len(filenames) > 10:
            print(f"{sub_indent}... and {len(filenames)-10} more")

if __name__ == "__main__":
    main()
