#!/usr/bin/env python3
"""Install the read-only TCP snapshot plugin into an existing PRIVATE test root.

Does not connect to the source, launch loggerd or change host services.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import fcntl
import shutil
import tempfile
from pathlib import Path

WRAPPER = '''#!/bin/sh
set -eu
exec /usr/bin/python3 /home/meteohub/live_feed_plugin.py /data/tcp-feed/feed.json /data/tcp-feed/state
'''

PREVIOUS_PLUGIN_SHA = '5a1636d65332a29de474a7f0e2d2e4f3a32f41b9d7efca764f92a6a53428cb80'
PRESSURE_POLICY = 'Complete source THB to native logger; dashboard uses pressure only'


def probe_tool():
    spec = importlib.util.spec_from_file_location('probe', Path(__file__).with_name('probe-cgi.py'))
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def check_config(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 262144:
        raise ValueError('Generate a private regular logger.conf first')
    entries = [line.split() for line in path.read_text().splitlines() if line.split()]
    stations = [p for p in entries if p[0] == '@WEATHERSTATION']
    if len(stations) != 1 or stations[0][:5] != ['@WEATHERSTATION', '0', '9', '5', '/home/meteohub/plugin.sh']:
        raise ValueError('Expected exactly station 0, connection Plug-in, path /home/meteohub/plugin.sh; no changes made')
    for key, value in (('@DATAPATH', '/data/weather/'), ('@ERRORLOG', '/data/log/meteohub.log')):
        if [p for p in entries if p[0] == key] != [[key, value]]:
            raise ValueError('Unexpected private data/log path; no changes made')


def verify_prepared(runtime, allow_previous=False):
    probe_tool().verify_runtime(runtime)
    check_config(runtime/'root/home/meteohub/logger.conf')
    manifest = runtime/'tcp-plugin-prepared.json'
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError('Prepare the private TCP plugin first')
    record = json.loads(manifest.read_text())
    expected = {
        'root/home/meteohub/plugin.sh': WRAPPER.encode(),
        'root/home/meteohub/live_feed_plugin.py':
            (Path(__file__).resolve().parent.parent/'live_feed_plugin.py').read_bytes(),
    }
    if record.get('schema') != 1 or set(record.get('files', {})) != set(expected):
        raise ValueError('Unexpected plugin preparation manifest')
    for name, data in expected.items():
        path = runtime/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Installed private plugin differs from reviewed source')
        actual=path.read_bytes();digest=hashlib.sha256(actual).hexdigest()
        previous=allow_previous and name.endswith('/live_feed_plugin.py') and digest==PREVIOUS_PLUGIN_SHA
        if actual!=data and not previous:
            raise ValueError('Installed private plugin differs from reviewed source; use plugin-update for the known previous release')
        if digest != record['files'][name]:
            raise ValueError('Prepared plugin hash mismatch')
    for name in ('root/data/tcp-feed', 'root/data/tcp-feed/state'):
        path = runtime/name
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError('Unexpected feed/state path')
    for name in ('feed.json', 'state/cursor.json', 'state/provenance.jsonl'):
        path = runtime/'root/data/tcp-feed'/name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('Unexpected feed/state file')


def prepare(runtime):
    runtime = runtime.resolve(strict=True)
    probe_tool().verify_runtime(runtime)
    home = runtime/'root/home/meteohub'
    check_config(home/'logger.conf')
    plugin = Path(__file__).resolve().parent.parent/'live_feed_plugin.py'
    code = plugin.read_bytes()
    files = {home/'plugin.sh': WRAPPER.encode(), home/'live_feed_plugin.py': code}
    feed = runtime/'root/data/tcp-feed'
    manifest = runtime/'tcp-plugin-prepared.json'
    for path in [*files, feed, manifest]:
        if path.exists() or path.is_symlink():
            raise ValueError('Preparation target already exists; leave existing data intact: ' + str(path))
    os.umask(0o077)
    created = []
    try:
        for path, content in files.items():
            with path.open('xb') as stream:
                created.append(path)
                stream.write(content)
            path.chmod(0o700)
        feed.mkdir(mode=0o700);created.append(feed)
        with manifest.open('x') as stream:
            created.append(manifest)
            json.dump({'schema': 1, 'status': 'prepared only; collector and logger not started',
                'plugin_sha256': hashlib.sha256(code).hexdigest(),
                'feed_path': '/data/tcp-feed/feed.json',
                'host_feed_path': str(feed/'feed.json'),
                'pressure_policy': PRESSURE_POLICY,
                'files': {str(p.relative_to(runtime)): hashlib.sha256(data).hexdigest() for p, data in files.items()},
            }, stream, indent=2)
            stream.write('\n')
    except Exception:
        for path in reversed(created):
            if path.is_dir(): path.rmdir()
            else: path.unlink()
        raise
    print('PREPARED: private plugin /home/meteohub/plugin.sh')
    print('HOST_FEED:', feed/'feed.json')
    print('PRESSURE: complete source THB sent to native logger; dashboard selects pressure only')
    print('No TCP connection, native logger or service started. Missing feed is expected until collector start.')


def replace_file(path,data,mode):
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            os.fchmod(stream.fileno(),mode)
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def update(runtime):
    runtime=runtime.resolve(strict=True)
    probe_tool().verify_runtime(runtime)
    fd=os.open(runtime/'.feed-consumer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        verify_prepared(runtime,allow_previous=True)
        target=runtime/'root/home/meteohub/live_feed_plugin.py'
        manifest=runtime/'tcp-plugin-prepared.json'
        code=(Path(__file__).resolve().parent.parent/'live_feed_plugin.py').read_bytes()
        if target.read_bytes()==code:
            print('REUSE: native THB plugin already installed');return
        backup=Path(tempfile.mkdtemp(prefix='tcp-plugin-before-',dir=runtime))
        for path in (target,manifest):shutil.copy2(path,backup/path.name)
        record=json.loads(manifest.read_text())
        digest=hashlib.sha256(code).hexdigest()
        record['files']['root/home/meteohub/live_feed_plugin.py']=digest
        record['plugin_sha256']=digest;record['pressure_policy']=PRESSURE_POLICY
        try:
            replace_file(target,code,0o700)
            replace_file(manifest,(json.dumps(record,indent=2)+'\n').encode(),0o600)
            verify_prepared(runtime)
        except Exception:
            for path,mode in ((target,0o700),(manifest,0o600)):
                replace_file(path,(backup/path.name).read_bytes(),mode)
            raise
        print('BACKUP:',backup)
        print('UPDATED: native THB plugin; archive, cursor and station settings preserved')
        print('No service started. Assign THB channel 0 to thb0 in Sensors during the next bounded test.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('--update', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the normal login user, without sudo')
    try:
        update(args.runtime) if args.update else prepare(args.runtime)
    except (OSError, ValueError) as error:
        parser.exit(1, 'STOP: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
