#!/usr/bin/env python3
"""Build a Kodi-repository layout for this TMDb Helper fork into dist/ (gitignored).

Same shape as Purple-Drain/skin.arctic.fuse.3's tools/build-repo.py and TheRedWizard's
tools/build-repo.sh, so repository.purpledrain can read this fork's gh-pages feed:

  dist/addons.xml
  dist/addons.xml.md5
  dist/plugin.video.themoviedb.helper/plugin.video.themoviedb.helper-<version>.zip
  dist/plugin.video.themoviedb.helper/icon.png, fanart.jpg

Versions follow the faux-fork rule (TheRedWizard docs/faux-fork-pattern.md): <upstream>+pd.N.
Usage: python3 tools/build-repo.py
"""
import hashlib
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'dist')
SKIP_DIRS = {'.git', '.github', '.claude', 'tools', 'dist', '__pycache__'}
SKIP_FILES = {'CLAUDE.md', '.gitattributes', '.gitignore', '.DS_Store', 'Thumbs.db'}
SKIP_SUFFIXES = ('.pyc', '.pyo', '.xcf', '~')

# Dependencies published alongside the add-on, so repository.purpledrain can satisfy them without
# repository.jurialmunkey enabled. Worked out on every build from addon.xml's own <import>s: any
# dependency jurialmunkey's repo publishes (script.module.jurialmunkey, script.module.infotagger)
# is bundled at his latest version, unmodified. Same method as Purple-Drain/skin.arctic.fuse.3's
# tools/build-repo.py. Kodi built-ins and official-repo modules are left alone.
UPSTREAM_REPO = 'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/nexusrepo/zips/'
NEVER_BUNDLE = {'plugin.video.themoviedb.helper'}


def _version_tuple(v):
    return tuple(int(p) if p.isdigit() else 0 for p in re.split(r'[.+~-]', v))


def resolve_bundled_deps():
    wanted = {i.get('addon'): i.get('version') for i in ET.parse(os.path.join(ROOT, 'addon.xml')).getroot().iter('import')}
    index = ET.fromstring(urllib.request.urlopen(UPSTREAM_REPO + 'addons.xml', timeout=60).read())
    upstream = {a.get('id'): a.get('version') for a in index.iter('addon')}
    deps = []
    for dep_id, minimum in sorted(wanted.items()):
        if dep_id in NEVER_BUNDLE or dep_id not in upstream:
            continue
        latest = upstream[dep_id]
        if minimum and _version_tuple(latest) < _version_tuple(minimum):
            sys.exit('%s: add-on needs %s but upstream only has %s' % (dep_id, minimum, latest))
        deps.append((dep_id, latest, '%s%s/%s-%s.zip' % (UPSTREAM_REPO, dep_id, dep_id, latest)))
    return deps


def main():
    root_el = ET.parse(os.path.join(ROOT, 'addon.xml')).getroot()
    addon_id, version = root_el.get('id'), root_el.get('version')
    if not addon_id or not version:
        sys.exit('addon.xml has no id/version on the <addon> element')
    shutil.rmtree(OUT, ignore_errors=True)
    out_dir = os.path.join(OUT, addon_id)
    os.makedirs(out_dir)
    zip_path = os.path.join(out_dir, '%s-%s.zip' % (addon_id, version))
    count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for cur, dirs, files in os.walk(ROOT):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for f in sorted(files):
                if f in SKIP_FILES or f.endswith(SKIP_SUFFIXES):
                    continue
                full = os.path.join(cur, f)
                z.write(full, addon_id + '/' + os.path.relpath(full, ROOT).replace(os.sep, '/'))
                count += 1
    for art in ('icon.png', 'fanart.jpg'):
        if os.path.isfile(os.path.join(ROOT, art)):
            shutil.copy(os.path.join(ROOT, art), os.path.join(out_dir, art))
    manifests = [open(os.path.join(ROOT, 'addon.xml'), encoding='utf-8').read()]
    for dep_id, dep_version, url in resolve_bundled_deps():
        data = urllib.request.urlopen(url, timeout=60).read()
        dep_dir = os.path.join(OUT, dep_id)
        os.makedirs(dep_dir, exist_ok=True)
        dep_zip = os.path.join(dep_dir, '%s-%s.zip' % (dep_id, dep_version))
        with open(dep_zip, 'wb') as fh:
            fh.write(data)
        with zipfile.ZipFile(dep_zip) as dz:
            dep_manifest = dz.read('%s/addon.xml' % dep_id).decode('utf-8')
        dep_root = ET.fromstring(re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', dep_manifest).encode('utf-8'))
        if dep_root.get('id') != dep_id or dep_root.get('version') != dep_version:
            sys.exit('%s: zip addon.xml is %s %s, expected %s' % (dep_id, dep_root.get('id'), dep_root.get('version'), dep_version))
        manifests.append(dep_manifest)
        print('bundled %s-%s sha256=%s' % (dep_id, dep_version, hashlib.sha256(data).hexdigest()))
    body = '\n'.join(
        '\n'.join(('\t' + l if l.strip() else l) for l in re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', m).rstrip().splitlines())
        for m in manifests)
    addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n%s\n</addons>\n' % body
    ET.fromstring(addons_xml.encode('utf-8'))
    with open(os.path.join(OUT, 'addons.xml'), 'w', encoding='utf-8') as fh:
        fh.write(addons_xml)
    with open(os.path.join(OUT, 'addons.xml.md5'), 'w') as fh:
        fh.write(hashlib.md5(addons_xml.encode('utf-8')).hexdigest())
    print('built %s (%d files, %.1f MB)' % (os.path.relpath(zip_path, ROOT), count, os.path.getsize(zip_path) / 1e6))


if __name__ == '__main__':
    main()
