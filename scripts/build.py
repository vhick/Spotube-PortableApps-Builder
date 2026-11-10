#!/usr/bin/env python3
"""Spotube v6+ PortableApps-only: official Windows release -> validated ZIP.
No upstream install is performed; installed apps, user profiles and registry stay untouched.
All external binaries are verified against GitHub's release SHA-256 digest.
"""
from __future__ import annotations
import argparse
import configparser
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = 'team-spotube/spotube'
ASSET = 'Spotube-windows-x86_64-setup.exe'
REV = 'b1r2'
PINNED_DIGEST = {'v6.0.0': 'd7e073ead0707fcdfcc50074e88721b7df38dc10248eadafc346867e156c6e8d'}
WORK = Path(__file__).resolve().parent.parent
API = f'https://api.github.com/repos/{REPO}'
USER_AGENT = 'SpotubePortableAppsBuilder/1.0 (+https://github.com/team-spotube/spotube)'


def require(cond: bool, msg: str) -> None:
    if not cond: raise RuntimeError(msg)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def request(url: str):
    parts = urllib.parse.urlsplit(url)
    require(parts.scheme == 'https' and parts.hostname in {'github.com', 'api.github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}, f'Untrusted source URL: {url}')
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': USER_AGENT, 'X-GitHub-Api-Version': '2022-11-28'}
    if os.getenv('GH_TOKEN'): headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    return urllib.request.Request(url, headers=headers)


def api_json(path: str, allow404=False):
    try:
        with urllib.request.urlopen(request(API + path), timeout=60) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        if e.code == 404 and allow404: return None
        raise RuntimeError(f'GitHub API error HTTP {e.code} on {path}; do not treat 401/403/429/5xx as missing') from e


def stable_num(tag: str):
    m = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', tag)
    return tuple(map(int, m.groups())) if m else None


def find_release(version: str):
    if version:
        tag = 'v' + version.lstrip('v')
        require(stable_num(tag) is not None, 'Only explicit stable X.Y.Z versions are accepted')
        release = api_json('/releases/tags/' + tag, allow404=True)
        require(release is not None, f'Upstream release not found: {tag}')
        releases = [release]
    else:
        releases = []
        for page in range(1, 6):
            batch = api_json(f'/releases?per_page=100&page={page}')
            require(isinstance(batch, list), 'Unexpected GitHub API releases response')
            releases += batch
            if len(batch) < 100: break
        else:
            raise RuntimeError('Pagination bound reached; refusing uncertain latest release')
    candidates = sorted((r for r in releases if stable_num(r.get('tag_name', '')) is not None
        and not r.get('draft') and not r.get('prerelease')), key=lambda r: stable_num(r['tag_name']), reverse=True)
    for r in candidates:
        match = [a for a in r.get('assets', []) if a.get('name') == ASSET]
        if match:
            require(len(match)==1, 'Duplicate official asset names')
            return r, match[0]
    raise RuntimeError('No appropriate stable official Windows installer asset found; no nightly/beta or installer substitutions')


def run(*args, cwd=None) -> None:
    print('+', ' '.join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def verify_agpl_license(path: Path) -> str:
    """Require the real complete upstream AGPLv3 license, while tolerating a BOM/blank lines.

    Some source files begin with UTF-8 BOM or harmless leading whitespace.
    Checking the exact byte prefix reports a false missing-license error.
    Return the original content unchanged for package license attribution.
    """
    require(path.is_file(), f'Upstream license file missing: {path}')
    raw = path.read_bytes()
    require(len(raw) > 15000, f'Upstream AGPL license unexpectedly short: {path}')
    try:
        content = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise RuntimeError(f'Upstream license is not valid UTF-8: {path}') from exc
    normalized = content.lstrip(' \t\r\n')
    require(re.match(r'GNU AFFERO GENERAL PUBLIC LICENSE\s+Version 3,\s*19 November 2007\b',
                     normalized) is not None and
            'TERMS AND CONDITIONS' in normalized and
            'END OF TERMS AND CONDITIONS' in normalized,
            f'Upstream LICENSE is not the expected complete GNU AGPL version 3: {path}')
    print(f'UPSTREAM LICENSE VERIFIED: AGPLv3, {len(raw)} bytes, SHA-256 {hashlib.sha256(raw).hexdigest()}', flush=True)
    return content


def git_checkout(tag, dest: Path):
    require(not dest.exists(), 'Existing upstream checkout path; clean before build')
    run('git', 'clone', '--quiet', '--depth', '1', '--branch', tag,
        f'https://github.com/{REPO}.git', dest)
    commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=dest, text=True).strip()
    require(re.fullmatch(r'[0-9a-f]{40}', commit) is not None, 'Unverified upstream commit identity')
    # Tag was fetched, not master/main. Inspect product version from the exact source.
    gradle = dest/'composeApp'/'build.gradle.kts'
    require(gradle.is_file(), 'Unexpected upstream v6+ source layout')
    text = gradle.read_text(encoding='utf-8')
    match = re.search(r'val version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', text)
    require(bool(match) and ('v'+match.group(1))==tag, 'Tag and official application version disagree')
    verify_agpl_license(dest/'LICENSE')
    return commit


def download_asset(asset, tag: str, dest: Path):
    digest = asset.get('digest') or ''
    if digest:
        require(re.fullmatch('sha256:[0-9a-fA-F]{64}', digest) is not None, f'Unsupported GitHub release digest {digest}')
        expected = digest[7:].lower()
    else:
        expected = PINNED_DIGEST.get(tag)
        require(expected is not None, 'GitHub release does not supply SHA-256 digest; add a reviewed pin for this exact tag before using it')
    if tag in PINNED_DIGEST:
        require(expected == PINNED_DIGEST[tag], 'Official digest contradicts pinned, source-inspected v6 release digest')
    url = asset.get('browser_download_url','')
    require(url == f'https://github.com/{REPO}/releases/download/{tag}/{ASSET}', 'Unexpected release asset provenance or URL')
    dest.parent.mkdir(parents=True,exist_ok=True)
    temp = dest.with_suffix('.partial')
    try:
        # Only GitHub-owned redirects are permitted; urllib follows HTTPS redirects.
        with urllib.request.urlopen(request(url), timeout=120) as inp, temp.open('wb') as out:
            shutil.copyfileobj(inp,out,1024*1024)
        require(temp.stat().st_size == asset['size'], 'Downloaded asset size disagrees with GitHub release record')
        require(sha(temp) == expected, 'Official installer SHA-256 verification FAILED')
        temp.replace(dest)
    finally:
        temp.unlink(missing_ok=True)
    return expected


def pe_machine(path: Path) -> int:
    with path.open('rb') as f:
        dos=f.read(64)
        require(len(dos)==64 and dos[:2]==b'MZ',f'Not a Windows PE: {path}')
        off=struct.unpack_from('<I',dos,0x3C)[0]
        require(off >= 64 and off < path.stat().st_size-24, f'Bad PE offset: {path}')
        f.seek(off)
        pe=f.read(6)
        require(pe[:4] == b'PE\0\0',f'Not a Windows PE: {path}')
        return struct.unpack_from('<H',pe,4)[0]


def sevenzip_exe() -> str:
    candidates = [shutil.which('7z'), shutil.which('7z.exe'), Path(os.environ.get('ProgramFiles','C:/Program Files'))/'7-Zip'/'7z.exe']
    for p in candidates:
        if p and Path(p).is_file(): return str(p)
    raise RuntimeError('7-Zip not found on hosted Windows runner')


def extract(official: Path, dest: Path):
    require(pe_machine(official) in (0x14c,0x8664), 'Unexpected official installer PE architecture')
    seven=sevenzip_exe()
    dest.mkdir(parents=True,exist_ok=False)
    run(seven,'x',str(official),'-y','-o'+str(dest))
    # Electron-builder/Nucleus NSIS can store an intermediate app-64.7z.
    # Do not execute the official installer; extraction must be noninteractive.
    for nested in sorted(dest.rglob('app-64.7z')):
        into = dest/'nested-payload'
        require(not into.exists(), 'Multiple conflicting app payloads')
        into.mkdir()
        run(seven,'x',str(nested),'-y','-o'+str(into))
    candidates=[p for p in dest.rglob('*') if p.is_file() and p.name.lower() == 'spotube.exe']
    require(len(candidates)==1, f'Expected exactly one unpacked spotube.exe; found {len(candidates)}. Installer layout may have changed.')
    exe=candidates[0]
    require(pe_machine(exe)==0x8664, 'Unpacked upstream application is not x64')
    folder=exe.parent
    require(len([x for x in folder.iterdir() if x.is_file() or x.is_dir()]) >= 2, 'Application resources/libs not found beside executable')
    return folder


def install_app(src: Path, dest: Path):
    require(not dest.exists(), 'Refusing overwrite staging application directory')
    shutil.copytree(src, dest)
    match=next(p for p in dest.iterdir() if p.name.lower()=='spotube.exe')
    if match.name!='spotube.exe': match.rename(dest/'spotube.exe')
    require(pe_machine(dest/'spotube.exe')==0x8664, 'Staged application not x64 PE')


def make_launcher(root: Path, icon: Path):
    code = WORK/'launcher'/'SpotubePortable.cpp'
    require(code.is_file() and icon.is_file(), 'Missing launcher source or authentic upstream icon')
    build = WORK/'work'/'compile'; build.mkdir(parents=True,exist_ok=True)
    res = build/'SpotubePortable.rc'
    res.write_text(f'1 ICON "{icon.as_posix()}"\n',encoding='utf-8')
    run('rc.exe','/nologo','/fo'+str(build/'SpotubePortable.res'),str(res))
    run('cl.exe','/nologo','/std:c++17','/EHsc','/O2','/MT','/W4','/DUNICODE','/D_UNICODE',
        '/Fo'+str(build)+'\\','/Fe'+str(root/'SpotubePortable.exe'),str(code),str(build/'SpotubePortable.res'),
        '/link','/SUBSYSTEM:WINDOWS','User32.lib','Ole32.lib')
    require(pe_machine(root/'SpotubePortable.exe')==0x8664, 'Compiled launcher must be Windows x64 PE')


def png_icons(icon: Path, appinfo: Path):
    from PIL import Image
    with Image.open(icon) as im:
        for size in (16,32):
            im.resize((size,size),Image.Resampling.LANCZOS).save(appinfo/f'appicon_{size}.png',format='PNG')
    shutil.copy2(icon, appinfo/'appicon.ico')


def package_version(tag: str) -> str:
    nums=stable_num(tag); require(nums is not None,'Invalid semver')
    return '.'.join(map(str,(*nums,0)))


def zip_staging(stage: Path, out: Path):
    root=stage.parent
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in sorted(stage.rglob('*')):
            name=p.relative_to(root).as_posix()
            if p.is_dir(): z.writestr(name+'/',b'')
            elif p.is_file() and not p.is_symlink(): z.write(p,name)
            else: raise RuntimeError(f'Symlink or unexpected staged file: {p}')
    with zipfile.ZipFile(out) as z:
        require(z.testzip() is None,'ZIP CRC error')
        require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate ZIP members')
        require(any(n.endswith('/Data/TraceGuard/') for n in z.namelist()), 'Recovery folder absent in ZIP')


def validate_stage(stage: Path, tag: str):
    require(stage.name == 'SpotubePortable', 'Incorrect portable root folder name')
    launcher=stage/'SpotubePortable.exe'; app=stage/'App'/'Spotube'/'spotube.exe'
    require(pe_machine(launcher) == 0x8664 and pe_machine(app)==0x8664,'Compiled launcher/application PE is not x64')
    info=stage/'App'/'AppInfo'
    for n in ('appinfo.ini','appicon.ico','appicon_16.png','appicon_32.png'):
        require((info/n).stat().st_size > 20, f'Invalid metadata/icon: {n}')
    meta=configparser.ConfigParser(interpolation=None); meta.optionxform=str
    with (info/'appinfo.ini').open(encoding='utf-8-sig') as f: meta.read_file(f)
    require(meta['Details']['AppID']=='SpotubePortableUnofficial', 'Wrong package identity')
    require(meta['Version']['DisplayVersion']==tag.lstrip('v'),'Wrong version metadata')
    require(meta['Control']['Start']=='SpotubePortable.exe','Wrong launch target')
    require((stage/'Data'/'TraceGuard'/'Recovered').is_dir(), 'Missing Data/recovery root')
    require((stage/'Other'/'Source'/'SpotubePortable.cpp').is_file(), 'Missing launcher source')
    require((stage/'Other'/'Source'/'LICENSE-Spotube.txt').is_file(), 'Missing upstream license')
    require((stage/'Other'/'Source'/'SOURCE-STORAGE-CANDIDATES.json').is_file(), 'Missing tagged-source storage scan')
    require((stage/'Other'/'Source'/'BUILD-IDENTITY.json').is_file(), 'Missing provenance manifest')
    require(not (stage/'App'/'Spotube'/'unins000.exe').exists(), 'Unexpected conventional uninstaller embedded')
    for p in stage.rglob('*'):
        require(not p.is_symlink(),f'Symlink/reparse in staging: {p}')
    return True


def github_outputs(**kwargs):
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8',newline='\n') as f:
            for k,v in kwargs.items(): f.write(f'{k}={v}\n')


def build(version):
    require(sys.platform=='win32', 'Application compilation and NSIS extraction require hosted Windows runner')
    release,asset=find_release(version)
    tag=release['tag_name']; print(f'UPSTREAM: {tag}',flush=True)
    require(stable_num(tag) is not None and int(stable_num(tag)[0])>=6, 'v5 Flutter is a different architecture; v6+ source-backed recipe only')
    upstream=WORK/'work'/'upstream'
    commit=git_checkout(tag,upstream)
    official=WORK/'work'/'download'/ASSET
    officialhash=download_asset(asset,tag,official)
    folder=extract(official,WORK/'work'/'unpacked')
    stage=WORK/'staging'/'SpotubePortable'; appinfo=stage/'App'/'AppInfo'
    appinfo.mkdir(parents=True,exist_ok=False)
    install_app(folder,stage/'App'/'Spotube')
    icon=upstream/'composeApp'/'icons'/'stable'/'icon.ico'
    make_launcher(stage,icon)
    png_icons(icon,appinfo)
    (stage/'Data'/'TraceGuard'/'Recovered').mkdir(parents=True)
    (stage/'Data'/'Roaming').mkdir(parents=True)
    (stage/'Data'/'Local').mkdir(parents=True)
    (stage/'Other'/'Source').mkdir(parents=True)
    appini=f'''[Format]\nType=PortableApps.comFormat\nVersion=3.7\n\n[Details]\nName=Spotube Portable (Unofficial)\nAppID=SpotubePortableUnofficial\nPublisher=Team Spotube / Unofficial portable packaging\nHomepage=https://github.com/team-spotube/spotube\nCategory=Music & Video\nDescription=Unofficial portable packaging of the Spotube desktop music client\nLanguage=Multilingual\nTrademarks=Spotube name and icons belong to their respective owners\n\n[License]\nShareable=true\nOpenSource=true\nFreeware=true\nCommercialUse=true\nEULAVersion=1\n\n[Version]\nPackageVersion={package_version(tag)}\nDisplayVersion={tag[1:]}\n\n[Control]\nIcons=1\nStart=SpotubePortable.exe\n'''
    (appinfo/'appinfo.ini').write_text(appini,encoding='utf-8-sig')
    (stage/'Other'/'Source'/'LICENSE-Spotube.txt').write_bytes((upstream/'LICENSE').read_bytes())
    import audit_source
    audit_source.scan(upstream,stage/'Other'/'Source'/'SOURCE-STORAGE-CANDIDATES.json')
    (stage/'Other'/'Source'/'SpotubePortable.cpp').write_bytes((WORK/'launcher'/'SpotubePortable.cpp').read_bytes())
    buildid={'upstream_repo':REPO,'upstream_tag':tag,'upstream_commit':commit,'source_license':'AGPL-3.0-or-later',
        'official_asset':ASSET,'official_asset_sha256':officialhash,
        'upstream_gradle_versions_sha256':sha(upstream/'gradle'/'libs.versions.toml'),
        'upstream_gradle_wrapper_sha256':sha(upstream/'gradle'/'wrapper'/'gradle-wrapper.properties'),
        'launcher_source_sha256':sha(WORK/'launcher'/'SpotubePortable.cpp'),
        'launcher_binary_sha256':sha(stage/'SpotubePortable.exe'),'staged_app_sha256':sha(stage/'App'/'Spotube'/'spotube.exe'),
        'builder_revision':REV,'packager':'vhick/Portable-Package-Builder@v1.0.0',
        'publisher':'vhick/portable-release-publisher@v1.1.1','installer_engine':'custom-nsis'}
    release_tag=f'portable-spotube-{tag}-{commit[:10]}-{REV}'
    buildid['release_tag']=release_tag
    (stage/'Other'/'Source'/'BUILD-IDENTITY.json').write_text(json.dumps(buildid,indent=2)+'\n',encoding='utf-8')
    (stage/'Other'/'Source'/'SOURCE-OFFER.txt').write_text(
        'Corresponding upstream Spotube source (immutable commit):\n'
        f'https://github.com/{REPO}/tree/{commit}\n'
        f'https://github.com/{REPO}/archive/{commit}.zip\n'
        'Upstream Spotube: AGPL-3.0-or-later. Launcher source is beside this file.\n'
        'Other third-party software has its own notices in the upstream source and release.\n',encoding='utf-8')
    (stage/'README.txt').write_text('Spotube Portable - unofficial (x64)\n'
        'Launch SpotubePortable.exe. Keep Data when updating.\n'
        'An existing conventional Spotube profile in Windows AppData blocks launch for safety.\n'
        'Settings: Data\\Roaming and Data\\Local; residual recovery: Data\\TraceGuard.\n'
        'User-requested music downloads may still go to the Windows Downloads folder.\n'
        'Close tray children before moving the portable folder.\n'
        'App: https://github.com/team-spotube/spotube (AGPL-3.0-or-later).\n'
        'Portable packaging/launcher not endorsed by Spotube upstream.\n',encoding='utf-8')
    validate_stage(stage,tag)
    out=WORK/'out'; out.mkdir(exist_ok=True)
    zipfile_out=out/f'SpotubePortable_{tag[1:]}_{commit[:10]}_{REV}.zip'
    zip_staging(stage,zipfile_out)
    (out/(zipfile_out.name+'.sha256')).write_text(f'{sha(zipfile_out)}  {zipfile_out.name}\n',encoding='ascii')
    print('ZIP SHA256:',sha(zipfile_out),flush=True)
    github_outputs(tag=release_tag,zip=str(zipfile_out),version=tag[1:],commit=commit)
    return 0


def verify_zip(path: Path):
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None,'ZIP CRC failed')
        names=z.namelist()
        require(len(names)==len(set(names)),'Duplicate members')
        require(all(n.startswith('SpotubePortable/') and '..' not in n.split('/') and '\\' not in n for n in names), 'Unsafe ZIP paths')
        require('SpotubePortable/SpotubePortable.exe' in names,'No root launcher')
        require('SpotubePortable/App/Spotube/spotube.exe' in names,'No application EXE')
        require('SpotubePortable/Other/Source/BUILD-IDENTITY.json' in names,'No build identity')
        manifest=json.loads(z.read('SpotubePortable/Other/Source/BUILD-IDENTITY.json'))
        require(sha_bytes(z.read('SpotubePortable/SpotubePortable.exe'))==manifest['launcher_binary_sha256'],'Launcher checksum mismatch')
        require(sha_bytes(z.read('SpotubePortable/App/Spotube/spotube.exe'))==manifest['staged_app_sha256'],'App checksum mismatch')
        github_outputs(tag=manifest['release_tag'],version=manifest['upstream_tag'][1:],commit=manifest['upstream_commit'])
        print('VERIFIED ZIP',path,manifest['upstream_tag'],manifest['upstream_commit'])

def sha_bytes(b): return hashlib.sha256(b).hexdigest()


def verify_installer(path):
    require(path.is_file() and path.stat().st_size>10000, 'Missing/too small installer')
    require(pe_machine(path) in (0x14c,0x8664), 'Installer stub is not PE x86/x64')
    seven=sevenzip_exe()
    p=subprocess.run([seven,'l',str(path)],capture_output=True,text=True,errors='replace',check=False)
    require(p.returncode==0,'7-Zip unable to list installer payload')
    text=p.stdout.lower()
    require('spotubeportable.exe' in text and 'spotube.exe' in text,'Installer payload missing Spotube Portable launcher/application')
    print('VALIDATED INSTALLER',path,sha(path))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build'); b.add_argument('--version',default='')
    v=sub.add_parser('verify-zip'); v.add_argument('zip',type=Path)
    i=sub.add_parser('verify-installer'); i.add_argument('installer',type=Path)
    args=parser.parse_args()
    if args.command=='build': build(args.version)
    elif args.command=='verify-zip': verify_zip(args.zip)
    else: verify_installer(args.installer)

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('FAILED:',exc,file=sys.stderr)
        sys.exit(1)
