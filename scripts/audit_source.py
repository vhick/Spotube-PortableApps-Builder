#!/usr/bin/env python3
"""Emit reproducible source-evidence references from the EXACT checked-out tag.
This is a textual candidate scan, NOT a claim that all runtime storage is known.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

PATTERNS = {
 'appdirs': r'AppDirs|appdirs|getUserDataDir|getUserConfigDir|getUserCacheDir',
 'datastore': r'DataStore|dataStore|PreferenceDataStore|createDataStore|settingsFile',
 'filesystem': r'File\(|Path\(|createDirectories|createDirectory|mkdir|fileKit|FileKit',
 'external_paths': r'APPDATA|LOCALAPPDATA|USERPROFILE|user\.home|ProgramData|Downloads|Desktop|Documents',
 'webview': r'WebView|webview|cookies|CookieManager|UserDataFolder|EBWebView',
 'integration': r'tray|Tray|Notification|notification|toast|AUMID|registry|HKEY|ShellExecute',
 'updater': r'AppUpdate|[Uu]pdater|restart|Restart|ProcessBuilder',
}

def scan(source: Path, output: Path):
    hits=[]; count=0
    compiled={name:re.compile(p,re.IGNORECASE) for name,p in PATTERNS.items()}
    for file in sorted((source/'composeApp').rglob('*')):
        if file.suffix not in ('.kt','.kts','.rs','.java','.xml') or not file.is_file(): continue
        count+=1
        for i,line in enumerate(file.read_text(encoding='utf-8',errors='replace').splitlines(),1):
            matched=[name for name,r in compiled.items() if r.search(line)]
            if matched:
                hits.append({'file':file.relative_to(source).as_posix(),'line':i,
                             'groups':matched,'source':line.strip()[:240]})
            if len(hits)>25000: raise RuntimeError('Source scan hit bound; revise patterns, do not silently truncate evidence')
    source_sha=hashlib.sha256((source/'composeApp'/'build.gradle.kts').read_bytes()).hexdigest()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'kind':'CANDIDATE SOURCE TEXT SCAN -- NOT COMPLETE STORAGE PROOF',
            'scanned_files':count,'build_gradle_sha256':source_sha,
            'matched_lines':hits},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'SOURCE CANDIDATE SCAN: {count} source files, {len(hits)} candidate lines',flush=True)

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('Usage: audit_source.py UPSTREAM_DIR OUTPUT_JSON')
    scan(Path(sys.argv[1]),Path(sys.argv[2]))
