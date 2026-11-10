"""End-to-end *synthetic fixture only* (Windows). Exercises compiled PE + TraceGuard.
Uses completely isolated temporary APPDATA and LOCALAPPDATA; no real host paths.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parent.parent
source=root/'staging'/'SpotubePortable'/'SpotubePortable.exe'
assert source.is_file(), 'Compile real launcher first'
with tempfile.TemporaryDirectory(prefix='SpotubeFixture-') as td:
    tmp=Path(td)
    portable=tmp/'Unicode Path 测试'/'SpotubePortable'
    app=portable/'App'/'Spotube'
    app.mkdir(parents=True)
    shutil.copy2(source,portable/'SpotubePortable.exe')
    fake=tmp/'fixture_spotube.exe'
    cmd=['cl.exe','/nologo','/EHsc','/std:c++17','/O2','/Fe:'+str(fake),
         str(root/'tests'/'fixture_spotube.cpp'),'/link','/SUBSYSTEM:CONSOLE']
    subprocess.run(cmd,check=True,cwd=tmp,timeout=60)
    shutil.copy2(fake,app/'spotube.exe')
    host=tmp/'IsolatedHost'; roaming=host/'Roaming';local=host/'Local'
    roaming.mkdir(parents=True); local.mkdir(parents=True)
    env=os.environ.copy()
    env['APPDATA']=str(roaming);env['LOCALAPPDATA']=str(local)
    env['SPOTUBE_TEST_HOST_LOCAL']=str(local)
    env['SPOTUBE_PORTABLE_SILENT_ERRORS']='1'
    saved=portable/'Data'/'TraceGuard'/'Recovered'/'Local_Spotube'
    for i in (1,2):
        process=subprocess.run([str(portable/'SpotubePortable.exe'),'--fixture-argument'],
                    env=env,cwd=tmp,timeout=30,check=False)
        assert process.returncode==0, f'Launcher fixture run {i} failed with {process.returncode}'
        assert not (local/'Spotube').exists(), 'Synthetic host folder not recovered after shutdown'
        assert (saved/'EmptyA'/'EmptyB').is_dir(), 'Nested completely-empty directories lost'
        assert (saved/'session.txt').read_text().strip()==str(i), 'Session restoration failed'
        assert (portable/'Data'/'Roaming'/'portability-test.txt').read_text().strip()=='test-data', 'Child APPDATA not redirected'
        assert not (portable/'Data'/'TraceGuard'/'active.txt').exists(), 'Unfinished transaction after normal exit'
        print(f'PASS synthetic launcher run #{i}: child env, empty dirs, state recovery, complete process exit')
print('WINDOWS SYNTHETIC FIXTURE PASSED; this is NOT real Spotube runtime validation')
