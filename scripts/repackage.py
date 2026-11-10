#!/usr/bin/env python3
"""Verify a trusted previously published ZIP and stage it for installer-only workflow."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import zipfile
import build

ROOT=Path(__file__).resolve().parent.parent
DOWNLOAD=ROOT/'download'

def main():
    zips=list(DOWNLOAD.glob('*.zip'))
    build.require(len(zips)==1,'Require exactly one earlier PortableApps ZIP')
    sums=DOWNLOAD/'SHA256SUMS.txt'
    build.require(sums.is_file(),'Missing publisher SHA256SUMS.txt')
    entries={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
        build.require(bool(m),'Invalid checksum line')
        entries[m.group(2)]=m.group(1)
    build.require(zips[0].name in entries,'Published ZIP not covered by checksum')
    build.require(build.sha(zips[0])==entries[zips[0].name],'Published checksum mismatch')
    build.verify_zip(zips[0])
    stage=ROOT/'staging'/'SpotubePortable'
    build.require(not stage.exists(),'Staging folder already exists')
    stage.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zips[0]) as z:
        for info in z.infolist():
            p=Path(info.filename)
            build.require(p.parts[0]=='SpotubePortable' and '..' not in p.parts,'Unsafe ZIP member')
            # Refuse symbolic links when extracting untrusted ZIP entries.
            build.require(((info.external_attr >> 16) & 0o170000)!=0o120000,'ZIP symlink forbidden')
            out=stage.parent.joinpath(*p.parts)
            if info.is_dir(): out.mkdir(parents=True,exist_ok=True)
            else:
                out.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src,out.open('wb') as dst:
                    import shutil; shutil.copyfileobj(src,dst)
    identity=json.loads((stage/'Other'/'Source'/'BUILD-IDENTITY.json').read_text(encoding='utf-8'))
    build.require(identity['builder_revision'] in {'b1r1','b1r2','b1r3'},'Unexpected builder revision; audit newer source before repackage')
    build.require(build.sha(stage/'SpotubePortable.exe')==identity['launcher_binary_sha256'],'Launcher changed')
    build.validate_stage(stage,identity['upstream_tag'])
    revision=os.environ.get('REPACKAGE_REVISION','r1')
    build.require(bool(re.fullmatch(r'r[1-9][0-9]*',revision)),'Repackage revision must be r1, r2, ...')
    tag=identity['release_tag'] + '-installer-' + revision
    build.github_outputs(tag=tag,version=identity['upstream_tag'][1:])
    print('REPACKAGED FROM VERIFIED BUILD IDENTITY',identity['upstream_commit'],tag)

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('FAILED:',exc,file=sys.stderr);sys.exit(1)
