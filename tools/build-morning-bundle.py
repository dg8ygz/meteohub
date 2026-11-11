#!/usr/bin/python3
"""Build reproducible single-file delivery from reviewed first-party sources."""
import argparse
import base64
import hashlib
import io
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
FILES=('morning-maintenance.py','host-status-pi50.py','quiet-checkpoint.py')


def build():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in FILES:
            info=zipfile.ZipInfo(name,date_time=(2026,11,12,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16
            z.writestr(info,(ROOT/name).read_bytes())
    payload=buf.getvalue()
    return ('''#!/usr/bin/python3
# Meteohub morning maintenance bundle. No action runs until explicitly requested.
import base64,hashlib,io,runpy,tempfile,zipfile
from pathlib import Path
PAYLOAD = '''+repr(base64.b64encode(payload).decode())+'''
if __name__ == '__main__':
    data=base64.b64decode(PAYLOAD)
    assert hashlib.sha256(data).hexdigest()=='''+repr(hashlib.sha256(payload).hexdigest())+'''
    bundle=Path(__file__).resolve()
    with tempfile.TemporaryDirectory(prefix='meteohub-morning-') as td:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert set(z.namelist())=='''+('set('+repr(FILES)+')')+'''
            for name in z.namelist():
                Path(td,name).write_bytes(z.read(name))
        runpy.run_path(str(Path(td,'morning-maintenance.py')),run_name='__main__',
                       init_globals={'BUNDLE_FILE':bundle})
''').encode()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    data=build();a.output.write_bytes(data)
    print(hashlib.sha256(data).hexdigest(),a.output)
