#!/usr/bin/python3
"""Pi .50 morning maintenance: prepare, apply, check, rollback.

Bundle runner supplies BUNDLE_FILE. Permanent writes require a normal ext4
maintenance boot; never edit a lower layer underneath a mounted host overlay.
No action reboots automatically. Native binaries/configuration are untouched.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

ROOT_UUID='15f4c6be-1102-4331-9904-f78e78afd1fd'
BOOT_UUID='B2F0-82D2'
PERSIST_UUID='6d332cf5-8a19-4fc5-bcaa-5156ab2dad54'
BASE=Path('/usr/local/libexec/meteohub-ram.py')
BASE_SHA='d588b4cefdba8a5dea26d9f96420651e19a29922ad9187a5b77753f51d2023ad'
RUNTIME=Path('/home/meteohub/meteohub-staging/5.1e-runtime')
BOOT=Path('/boot/firmware');CMD=BOOT/'cmdline.txt'
STAGED=BOOT/'meteohub-morning-20261112.py'
PROOF=BOOT/'meteohub-morning-20261112.json'
DEST=Path('/usr/local/libexec/meteohub-maintenance-v1')
MANIFEST=DEST/'installation.json'
WEB='meteohub-web-test.service';LOGGER='meteohub-live-logger.service'
STATUS='meteohub-host-status.service';CHECKPOINT='meteohub-ram-checkpoint.service'
TOOLS=Path(__file__).resolve().parent


def run(*args,timeout=120):
    r=subprocess.run([str(x) for x in args],text=True,capture_output=True,timeout=timeout)
    if r.returncode:raise RuntimeError(str(args[0])+': '+r.stderr.strip()+' '+r.stdout.strip())
    return r.stdout.strip()


def show(unit,field):return run('systemctl','show',unit,'-p',field,'--value')
def sha(data):return hashlib.sha256(data).hexdigest()
def boot_id():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def atomic(path,data,mode=0o600):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.new-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fchmod(f.fileno(),mode);os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:Path(tmp).unlink(missing_ok=True)


def mount(path,uuid=None,kind=None,mode='ro'):
    data=json.loads(run('findmnt','-J','--mountpoint',path,'-o','UUID,FSTYPE,OPTIONS'))['filesystems'][0]
    if ((uuid and data['uuid']!=uuid) or (kind and data['fstype']!=kind)
            or mode not in data['options'].split(',')):
        raise ValueError('Unexpected mount: '+str(path))
    return data


@contextlib.contextmanager
def boot_writable():
    mount(BOOT,BOOT_UUID,'vfat')
    run('mount','-o','remount,rw',BOOT)
    try:yield
    finally:
        try:run('sync','-f',BOOT)
        finally:run('mount','-o','remount,ro',BOOT)


def change_boot(expected,replacement):
    if CMD.is_symlink():raise ValueError('Linked boot command line')
    old=CMD.read_bytes()
    if len(old.splitlines())!=1 or re.findall(rb'overlayroot=\S+',old)!=[expected.encode()]:
        raise ValueError('Unexpected overlayroot boot option')
    new=old.replace(expected.encode(),replacement.encode())
    with boot_writable():
        try:
            with CMD.open('wb') as f:f.write(new);f.flush();os.fsync(f.fileno())
            if CMD.read_bytes()!=new:raise ValueError('Boot readback mismatch')
        except BaseException:
            CMD.write_bytes(old);raise


def wait_ready():
    until=time.monotonic()+120
    announced=False
    while True:
        units=(WEB,LOGGER,'meteohub-dashboard-index.service','meteohub-web-test.socket')
        if (all(show(u,'ActiveState')=='active' for u in units)
                and run('timedatectl','show','-p','NTPSynchronized','--value')=='yes'):
            return
        if time.monotonic()>=until:raise ValueError('Boot readiness timeout; inspect units and NTP')
        if not announced:
            print('Warte auf bereits eingerichtete Zeitsynchronisation und Anwendungen ...',flush=True)
            announced=True
        time.sleep(2)


def basic():
    if sha(BASE.read_bytes())!=BASE_SHA:raise ValueError('Unexpected RAM helper version; no update attempted')
    mount('/srv/meteohub-persist',PERSIST_UUID,'ext4')
    mount(BOOT,BOOT_UUID,'vfat')
    report=json.loads(run('python3',BASE,'status'))
    if report['needs_attention'] or report.get('checkpoint_interval_minutes')!=360:
        raise ValueError('RAM/apps/six-hour schedule not ready')
    if show(WEB,'User')!='1000' or show(WEB,'ProtectProc')!='invisible' or show(WEB,'RootDirectory')!=str(RUNTIME/'root'):
        raise ValueError('Unexpected web service isolation')
    return report


def archive_proof():
    path=RUNTIME/'root/data/weather'/time.strftime('%Y%m',time.gmtime())/'raw'
    data=path.read_bytes()
    if not data:raise ValueError('Empty archive')
    return dict(path=str(path),bytes=len(data),sha256=sha(data))


def prefix_check(proof):
    with Path(proof['path']).open('rb') as f:data=f.read(proof['bytes'])
    if len(data)!=proof['bytes'] or sha(data)!=proof['sha256']:
        raise ValueError('Archive prefix was not preserved')


def prepare():
    mount('/',kind='overlay',mode='rw');mount('/media/root-ro',ROOT_UUID,'ext4')
    basic()
    if STAGED.exists() or PROOF.exists():raise ValueError('Preparation already exists; inspect before repeating')
    if show('systemd-remount-fs.service','Result')!='success':raise ValueError('Remount service not healthy')
    report=dict(boot_id=boot_id(),archive=archive_proof(),cmdline=CMD.read_text(),
                prepared_at=time.time(),bundle_sha256=sha(Path(BUNDLE_FILE).read_bytes()))
    # Preserve diagnostics outside volatile host overlay before the maintenance reboot.
    journal=run('journalctl','-b','--no-pager')
    with boot_writable():
        STAGED.write_bytes(Path(BUNDLE_FILE).read_bytes())
        PROOF.write_text(json.dumps(report,indent=2)+'\n')
        (BOOT/'meteohub-morning-20261112-journal.txt').write_text(journal)
        if sha(STAGED.read_bytes())!=report['bundle_sha256']:raise ValueError('Staged bundle readback mismatch')
    run('systemctl','start',CHECKPOINT,timeout=900)
    if show(CHECKPOINT,'Result')!='success':raise ValueError('Checkpoint failed; boot unchanged')
    change_boot('overlayroot=tmpfs:recurse=0','overlayroot=disabled')
    print('VORBEREITET: Paket und Diagnose auf Bootpartition gesichert.')
    print('Jetzt: systemctl reboot')
    print('Danach: python3 '+str(STAGED)+' apply')


def contents():
    unit=Path('/etc/systemd/system'); adapter=DEST/'host-status.py';quiet=DEST/'quiet-checkpoint.py'
    files={adapter:((TOOLS/'host-status-pi50.py').read_bytes(),0o755),
           quiet:((TOOLS/'quiet-checkpoint.py').read_bytes(),0o755),
           DEST/'real-ps':(Path('/usr/bin/ps').read_bytes(),0o755),
           DEST/'maintenance.py':(Path(BUNDLE_FILE).read_bytes(),0o700)}
    collector=f'''[Unit]
Description=Meteohub verified host service status
[Service]
Type=exec
User=root
UMask=0022
RuntimeDirectory=meteohub-host-status
RuntimeDirectoryMode=0755
RuntimeDirectoryPreserve=yes
ExecStartPre=/usr/bin/python3 {adapter} once
ExecStart=/usr/bin/python3 {adapter} collect
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX
ReadWritePaths=/run/meteohub-host-status
'''
    web=f'''[Unit]
Requires={STATUS}
After={STATUS}
[Service]
BindReadOnlyPaths={adapter}:/usr/bin/ps
BindReadOnlyPaths={DEST}/real-ps:/opt/meteohub-host-real-ps
BindReadOnlyPaths=/run/meteohub-host-status:/opt/meteohub-host-status
'''
    runtime=f'''[Service]
ExecStartPost=/usr/bin/python3 {adapter} links
'''
    checkpoint=f'''[Service]
ExecStart=
ExecStart=/usr/bin/python3 {quiet} checkpoint
ExecStopPost=/usr/bin/python3 {quiet} cleanup
'''
    thaw=f'''[Unit]
Description=Release Meteohub writers if a checkpoint exceeds 25 seconds
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {quiet} thaw
'''
    timer='[Timer]\nOnActiveSec=25s\nAccuracySec=1s\n'
    for path,text in {
        unit/STATUS:collector,
        unit/(WEB+'.d')/'60-host-status.conf':web,
        unit/'meteohub-live-runtime.service.d/60-native-status.conf':runtime,
        unit/(CHECKPOINT+'.d')/'60-quiet-checkpoint.conf':checkpoint,
        unit/'meteohub-checkpoint-thaw.service':thaw,
        unit/'meteohub-checkpoint-thaw.timer':timer,
    }.items():files[path]=(text.encode(),0o644)
    return files


def native_status():
    path=Path('/run/meteohub-live-1000/meteohub/logger.dat')
    try:
        value=int(path.read_text().strip());age=time.time()-value
        valid=value>0 and age>=-5
        return dict(path=str(path),native_timestamp=value,age_seconds=round(age,1),valid=valid,
                    note='Original logger timestamp; no synthetic data written')
    except (OSError,ValueError):return dict(path=str(path),valid=False,note='OPEN: native logger.dat missing/unreadable')


def web_probe():
    pid=show(WEB,'MainPID')
    code='''import json,pathlib,subprocess
v=pathlib.Path('/opt/meteohub-host-status')
s=json.loads((v/'status.json').read_text())
pids={x.split()[0] for x in subprocess.check_output(['/bin/ps','ax'],text=True).splitlines() if x.split()}
for name,row in s['services'].items():
 assert (pathlib.Path('/var/run')/name).read_text().strip()==str(row['pid']),name
 assert (str(row['pid']) in pids)==row['active'],name
print('PASS: native PID/ps status within private web namespace')
'''
    return run('nsenter','--target',pid,'--mount','--root','--wdns=/',
               '--setgid=1000','--setuid=1000','--','/usr/bin/python3','-c',code)


def apply():
    mount('/',ROOT_UUID,'ext4','rw');wait_ready();basic()
    proof=json.loads(PROOF.read_text())
    if boot_id()==proof['boot_id']:raise ValueError('Maintenance reboot has not happened')
    if sha(Path(BUNDLE_FILE).read_bytes())!=proof['bundle_sha256']:raise ValueError('Staged bundle changed')
    prefix_check(proof['archive'])
    if DEST.exists():raise ValueError('Installation directory already exists; use check or rollback')
    # Temporary test must have gone away with reboot. Do not mix incompatible adapters.
    if show(STATUS,'LoadState')!='not-found':raise ValueError('Existing status adapter must be reviewed')
    if any(':/usr/bin/ps' in x or ':/bin/ps' in x for x in show(WEB,'BindReadOnlyPaths').split()):
        raise ValueError('Foreign ps bind mount')
    files=contents()
    for path in files:
        if os.path.lexists(path):raise ValueError('Refusing existing destination: '+str(path))
        for parent in path.parents:
            if parent.is_symlink():raise ValueError('Linked destination parent')
    before=archive_proof();pid=show(LOGGER,'MainPID')
    backup=Path(tempfile.mkdtemp(prefix='meteohub-morning-before-',dir='/root'))
    (backup/'journal.txt').write_text(run('journalctl','-b','--no-pager'))
    (backup/'units.txt').write_text(run('systemctl','cat',WEB,LOGGER,CHECKPOINT))
    (backup/'cmdline.txt').write_bytes(CMD.read_bytes())
    manifest=dict(files={str(p):sha(data) for p,(data,mode) in files.items()},
                  backup=str(backup),archive=before,boot_id=boot_id())
    # Original helper and shutdown path are unchanged. All installed files are new.
    with open('/run/lock/meteohub-storage.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # A concurrent scheduled checkpoint must not leave an empty installation
        # directory that would prevent a later retry.
        DEST.mkdir(mode=0o755)
        DEST.chmod(0o755)
        try:
            atomic(MANIFEST,(json.dumps(manifest,indent=2)+'\n').encode())
            for path,(data,mode) in files.items():atomic(path,data,mode)
            run('systemd-analyze','verify','--man=no',
                '/etc/systemd/system/'+STATUS,'/etc/systemd/system/meteohub-checkpoint-thaw.service')
            run('python3',DEST/'host-status.py','links')
            run('systemctl','daemon-reload')
            run('systemctl','start',STATUS)
            run('systemctl','restart',WEB)
            print(web_probe())
            if show(LOGGER,'MainPID')!=pid:raise ValueError('Logger PID changed during status installation')
            prefix_check(before)
        except BaseException:
            # Keep package + manifest even on failure so rollback is repeatable.
            for path in files:
                if str(path).startswith('/etc/systemd/'):path.unlink(missing_ok=True)
            run('systemctl','daemon-reload');run('systemctl','restart',WEB)
            subprocess.run(['systemctl','stop',STATUS],capture_output=True)
            raise
    # The first real receiver checkpoint is explicit acceptance, outside storage lock.
    try:
        run('systemctl','start',CHECKPOINT,timeout=900)
        if show(CHECKPOINT,'Result')!='success':
            raise ValueError('First quiet checkpoint failed')
        if show(LOGGER,'MainPID')!=pid:
            raise ValueError('First quiet checkpoint changed logger PID')
        prefix_check(before);basic()
    except BaseException:
        rollback()
        raise
    report=dict(installed=True,logger_pid_unchanged=True,native=native_status(),
                check_boot_pending=True,backup=str(backup))
    (DEST/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
    # Leave an independently executable rollback package on the writable root.
    run('sync','-f',DEST)
    change_boot('overlayroot=disabled','overlayroot=tmpfs:recurse=0')
    print(json.dumps(report,indent=2))
    print('INSTALLIERT. Original-Logger und Konfiguration unveraendert; erster ruhiger Checkpoint erfolgreich.')
    print('Jetzt: systemctl reboot')
    print('Danach: python3 '+str(DEST/'maintenance.py')+' check')


def check():
    manifest=json.loads(MANIFEST.read_text())
    mount('/',kind='overlay',mode='rw');mount('/media/root-ro',ROOT_UUID,'ext4')
    wait_ready();report=basic();prefix_check(manifest['archive'])
    for path,digest in manifest['files'].items():
        if sha(Path(path).read_bytes())!=digest:raise ValueError('Installed file changed: '+path)
        if sha((Path('/media/root-ro')/path.lstrip('/')).read_bytes())!=digest:
            raise ValueError('Permanent lower copy differs: '+path)
    if boot_id()==manifest['boot_id']:raise ValueError('Post-install reboot not yet verified')
    if show(STATUS,'ActiveState')!='active':raise ValueError('Host status adapter inactive')
    print(web_probe())
    print('PASS: permanent files, host RO overlay, native status paths, all apps, archive prefix and 6h schedule.')
    print(json.dumps(dict(ram=report,native=native_status()),indent=2))
    print(run('journalctl','-b','-u',CHECKPOINT,'--no-pager','-n','12'))
    print('OPEN until observed: next scheduled freeze checkpoint and native page last-data display.')


def maintenance():
    mount('/',kind='overlay',mode='rw');mount('/media/root-ro',ROOT_UUID,'ext4')
    with boot_writable():
        (BOOT/'meteohub-morning-rollback-journal.txt').write_text(run('journalctl','-b','--no-pager'))
    change_boot('overlayroot=tmpfs:recurse=0','overlayroot=disabled')
    print('Wartungsstart vorbereitet. Jetzt systemctl reboot; danach:')
    print('python3 '+str(DEST/'maintenance.py')+' rollback')


def rollback():
    mount('/',ROOT_UUID,'ext4','rw')
    manifest=json.loads(MANIFEST.read_text())
    with open('/run/lock/meteohub-storage.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for path,digest in manifest['files'].items():
            if Path(path).exists() and sha(Path(path).read_bytes())!=digest:
                raise ValueError('Refusing changed installed file: '+path)
        run('python3',DEST/'quiet-checkpoint.py','cleanup')
        # Remove only additive units/drop-ins. Keep code/manifest for diagnosis.
        for path in manifest['files']:
            if path.startswith('/etc/systemd/'):Path(path).unlink(missing_ok=True)
        run('systemctl','daemon-reload');run('systemctl','restart',WEB)
        subprocess.run(['systemctl','stop',STATUS,'meteohub-checkpoint-thaw.timer'],capture_output=True)
        for name in ('dropbear.pid','smbd.pid','ntpd.pid'):
            p=Path('/run/meteohub-live-1000')/name
            if p.is_symlink() and os.readlink(p)=='/opt/meteohub-host-status/'+name:p.unlink()
    print('ROLLBACK: original checkpoint and web view restored. Native logger.dat directory retained.')
    print('Maintenance boot remains writable; re-enable overlay only after diagnosis.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','apply','check','maintenance','rollback'])
    args=parser.parse_args()
    if os.geteuid()!=0:parser.error('Bitte als root ausfuehren')
    os.umask(0o077)
    if 'BUNDLE_FILE' not in globals():raise ValueError('Use the downloadable bundle runner')
    globals()[args.action]()


if __name__=='__main__':
    try:main()
    except Exception as e:raise SystemExit('STOP: '+str(e))
