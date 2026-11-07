#!/usr/bin/env python3
"""Resumable Meteohub 5.1e preparation on Raspberry Pi OS Lite Trixie.

Run as the login user. No automatic licence acceptance, station selection or
production logger deployment. See docs/installer.md for the remaining gates.
"""
import argparse
import hashlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parent
RAR_SHA = 'eb0ba98acc31580de9416d1b3609ab38287aadb9af4edf1935edcbdff0ef11b2'
UPDATE_SHA = '725bf80186fe2e426e0caad80d6b5994c013fe7f918506fbfb62f5aef2826ad4'
PACKAGES = ['libc6:armhf','libssl3t64:armhf','python3-pyelftools','git','python3',
            'ca-certificates','file','binutils','curl','unrar-free','fdisk',
            'lighttpd','apache2-utils']
MASKED = ['lighttpd.service','lighttpd-maint.service','lighttpd-maint.timer']


def run(args, capture=False, check=True, **kw):
    env = dict(os.environ)
    for key in ('LD_PRELOAD','LD_AUDIT','LD_LIBRARY_PATH'):env.pop(key,None)
    return subprocess.run([str(x) for x in args],check=check,text=True,
                          capture_output=capture,env=env,**kw)


def load(name):
    spec = importlib.util.spec_from_file_location(name,REPO/'tools'/(name+'.py'))
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def helper(name,*args):
    return run([sys.executable,REPO/'tools'/(name+'.py'),*args])


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def download(url,target,expected):
    if target.is_symlink():raise ValueError('Download symlink refused: '+str(target))
    if target.exists():
        if not target.is_file() or sha(target)!=expected:raise ValueError('Existing download checksum mismatch: '+str(target))
        print('REUSE:',target,flush=True);return
    part=target.with_suffix(target.suffix+'.part')
    if part.exists() or part.is_symlink():
        raise ValueError('Incomplete download retained; inspect/remove only this partial file before retry: '+str(part))
    run(['curl','--fail','--location','--connect-timeout','20','--output',part,url])
    if sha(part)!=expected:raise ValueError('Downloaded checksum mismatch; partial file retained')
    part.rename(target)


def platform_check():
    osinfo=Path('/etc/os-release').read_text()
    arch=run(['dpkg','--print-architecture'],capture=True).stdout.strip()
    model=Path('/proc/device-tree/model')
    if 'VERSION_CODENAME=trixie' not in osinfo or arch!='arm64':
        raise ValueError('This installer requires the documented Trixie arm64 base')
    if not model.exists() or not re.search(r'Raspberry Pi [34] Model',model.read_text().rstrip('\0')):
        raise ValueError('This installer is scoped to Raspberry Pi 3/4 Model B')
    audit=run(['dpkg','--audit'],capture=True)
    if audit.stdout.strip():raise ValueError('dpkg --audit reports unfinished packages; finish them first')


def packages():
    foreign=run(['dpkg','--print-foreign-architectures'],capture=True).stdout.split()
    if 'armhf' not in foreign:run(['sudo','dpkg','--add-architecture','armhf'])
    missing=[]
    for package in PACKAGES:
        result=run(['dpkg-query','-W','-f=${Status}',package],capture=True,check=False)
        if result.returncode or result.stdout!='install ok installed':missing.append(package)
    for unit in MASKED:
        if run(['systemctl','is-active',unit],capture=True,check=False).stdout.strip()=='active':
            raise ValueError('Existing default web service/timer is active; refusing package installation: '+unit)
    if missing:
        run(['sudo','apt-get','update'])
        run(['apt-get','--simulate','install','--no-install-recommends',*missing])
    run(['sudo','systemctl','mask',*MASKED])
    if missing:
        # APT displays the actual plan and asks the operator before installation.
        run(['sudo','apt-get','install','--no-remove','--no-install-recommends',*missing])
    if run(['sudo','dpkg','--audit'],capture=True).stdout.strip():
        raise ValueError('Package configuration remains incomplete')
    run(['/lib/ld-linux-armhf.so.3','--version'],capture=True)


class Installer:
    def __init__(self,home):
        self.home=home
        self.original=home/'meteohub-original'
        self.work=home/'meteohub-staging'
        self.base=self.work/'5.0s-openssl3'
        self.candidate=self.work/'5.1e-openssl3'
        self.runtime=self.work/'5.1e-runtime'
        self.mount=Path('/mnt/meteohub-original')
        for path in (home,self.original,self.work,self.base,self.candidate,self.runtime):
            if path.is_symlink() or any(c.isspace() or c in ':\\%\"\'' for c in str(path)):
                raise ValueError('Use ordinary directories without special path characters')

    def loop(self):
        record=self.original/'image-loop.device'
        if record.is_symlink():raise ValueError('Loop record symlink refused')
        device=record.read_text().strip()
        if not re.fullmatch(r'/dev/loop[0-9]+',device):raise ValueError('Invalid saved loop device')
        backing=run(['sudo','losetup','--noheadings','--raw','--output','BACK-FILE',device],capture=True).stdout.strip()
        if Path(backing)!=self.original/'mhrpi-v5.0s.img':raise ValueError('Saved loop device belongs to another image')
        if run(['sudo','blockdev','--getro',device],capture=True).stdout.strip()!='1':raise ValueError('Loop device is not read-only')
        return device

    def mount_image(self):
        image=self.original/'mhrpi-v5.0s.img'
        if image.is_symlink() or not image.is_file() or image.stat().st_size!=1970274304:
            raise ValueError('Unexpected original image type/size')
        table=json.loads(run(['/usr/sbin/sfdisk','--json',image],capture=True).stdout)['partitiontable']
        parts=table['partitions']
        if table.get('sectorsize')!=512 or len(parts)!=3 or (parts[1]['start'],parts[1]['size'],parts[1]['type'])!=(104448,3481600,'83'):
            raise ValueError('Unexpected vendor image partition layout')
        record=self.original/'image-loop.device'
        if record.exists() or record.is_symlink():device=self.loop()
        else:
            device=run(['sudo','losetup','--find','--show','--read-only','--partscan',image],capture=True).stdout.strip()
            with record.open('x') as stream:stream.write(device+'\n')
            run(['sudo','udevadm','settle'])
        result=run(['findmnt','--json','--mountpoint',self.mount],capture=True,check=False)
        if result.returncode==0:
            fs=json.loads(result.stdout)['filesystems'][0]
            opts=set(fs['options'].split(','))
            if fs['source']!=device+'p2' or fs['fstype']!='ext3' or not {'ro','nodev','nosuid','noexec'}<=opts or not {'noload','norecovery'}&opts:
                raise ValueError('Existing mount does not match the read-only vendor image')
        else:
            if self.mount.is_symlink():raise ValueError('Image mountpoint symlink refused')
            run(['sudo','mkdir','-p',self.mount])
            if any(self.mount.iterdir()):raise ValueError('Image mountpoint is not empty')
            run(['sudo','mount','-t','ext3','-o','ro,noload,nodev,nosuid,noexec',device+'p2',self.mount])
        print('PASS: original image mounted read-only',flush=True)

    def prepare(self):
        platform_check();run(['sudo','-v']);packages()
        self.original.mkdir(mode=0o700,exist_ok=True)
        self.work.mkdir(mode=0o700,exist_ok=True)
        image=self.original/'mhrpi-v5.0s.img'
        if not image.exists() and shutil.disk_usage(self.home).free<5*1024**3:
            raise ValueError('At least 5 GiB free is required for initial downloads/extraction')
        download('https://www.meteohub.de/files/mhrpi-v5.0s.rar',self.original/'mhrpi-v5.0s.rar',RAR_SHA)
        if not image.exists():run(['unrar-free','-x','mhrpi-v5.0s.rar'],cwd=self.original)
        self.mount_image()
        if not self.base.exists():helper('stage-openssl3',self.mount,self.base)
        else:load('probe-cgi').verify(self.base);print('REUSE:',self.base,flush=True)
        update=self.original/'update-v5.1e.upd'
        download('https://www.meteohub.de/files/update-v5.1e.upd',update,UPDATE_SHA)
        if not self.candidate.exists():helper('stage-update',update,self.base,self.candidate)
        else:
            load('probe-cgi').verify(self.candidate)
            manifest=json.loads((self.candidate/'manifest.json').read_text())
            if manifest.get('application_version')!='5.1e' or manifest.get('update_sha256')!=UPDATE_SHA:
                raise ValueError('Existing candidate is not the pinned 5.1e update')
            print('REUSE:',self.candidate,flush=True)
        for name in ('loggerd','meteometar','meteonet','meteoschedule','meteohub.cgi'):
            run(['/lib/ld-linux-armhf.so.3','--library-path',str(self.candidate/'lib')+':/usr/lib/arm-linux-gnueabihf','--list',self.candidate/'bin'/name])
        if not self.runtime.exists():helper('stage-runtime',self.mount,self.candidate,self.runtime)
        else:load('probe-cgi').verify_runtime(self.runtime);print('REUSE:',self.runtime,flush=True)
        print('PREPARED: 5.1e core and private runtime; native logger not installed',flush=True)

    def web(self):
        tool=load('web-test');tool.check_paths(self.candidate,self.runtime)
        web=self.runtime/'root/opt/meteohub-web'
        if not web.exists():tool.prepare(self.candidate,self.runtime)
        result=run(['systemctl','show','meteohub-web-test.service','-p','ActiveState','-p','RootDirectory','-p','BindReadOnlyPaths'],capture=True,check=False)
        fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        if fields.get('ActiveState')=='active':
            if fields.get('RootDirectory')!=str(self.runtime/'root') or str(self.candidate/'bin')+':' not in fields.get('BindReadOnlyPaths',''):
                raise ValueError('Another test runtime is active; refusing to replace it')
            print('REUSE: running 5.1e browser test',flush=True)
        else:tool.start(self.candidate,self.runtime)
        print('WEB: http://127.0.0.1:18090/cgi-bin/meteohub.cgi (SSH tunnel)',flush=True)
        print('Manual: read/accept licence terms, verify version/build, select station 0 Plug-in /home/meteohub/plugin.sh.',flush=True)

    def feed_test(self,host,port,duration):
        if not host:raise ValueError('Provide --source-host for the existing TCP-copy service')
        fd=os.open(self.runtime/'.feed-consumer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            run(['sudo','-v'])
            helper('probe-cgi',self.candidate,'--runtime',self.runtime,'--generate-logger-config')
            tool=load('prepare-tcp-plugin')
            if (self.runtime/'tcp-plugin-prepared.json').exists():tool.verify_prepared(self.runtime)
            else:tool.prepare(self.runtime)
            helper('tcp-feed','--host',host,'--port',str(port),'--duration',str(duration),
                   '--output',self.runtime/'root/data/tcp-feed/feed.json')
            helper('probe-cgi',self.candidate,'--runtime',self.runtime,'--probe-plugin')
            print('TEST FINISHED: collector/plugin stopped; no native logger started',flush=True)

    def status(self):
        for label,path in [('image',self.original/'mhrpi-v5.0s.img'),('5.1e',self.candidate/'manifest.json'),
                           ('runtime',self.runtime/'runtime-manifest.json'),('plugin',self.runtime/'tcp-plugin-prepared.json')]:
            print(label+': '+('present' if path.is_file() else 'not prepared'))
        print('Presence is not a functional acceptance; see the private probe reports.')
        run(['systemctl','show','meteohub-web-test.service','meteohub-dashboard-index.service','-p','Id','-p','ActiveState'],check=False)

    def storage_check(self):
        print('READ ONLY INVENTORY: no mounts, services or boot settings changed',flush=True)
        for command in (['free','-h'],['swapon','--show'],['findmnt','-T','/'],
                        ['findmnt','-T','/boot/firmware'],['lsblk','-o','NAME,SIZE,FSTYPE,MOUNTPOINTS']):
            run(command,check=False)
        for relative in ('root/data','root/data/weather','root/data/dashboard',
                         'root/data/tcp-feed','root/home/meteohub'):
            path=self.runtime/relative
            if path.is_symlink():raise ValueError('Linked runtime path refused: '+relative)
            if path.exists():run(['du','-sx','--block-size=1',path],timeout=30)
            else:print('NOT PRESENT:',relative)
        print('One inventory is not a daily growth measurement or a read-only acceptance.',flush=True)

    def unmount(self):
        device=self.loop()
        result=run(['findmnt','-n','-o','SOURCE','--mountpoint',self.mount],capture=True,check=False)
        if result.returncode==0:
            if result.stdout.strip()!=device+'p2':raise ValueError('Mount belongs to another source')
            run(['sudo','umount',self.mount])
        run(['sudo','losetup','--detach',device])
        (self.original/'image-loop.device').unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('install','prepare','web','feed-test','native-test','plugin-update','extension-update','extension-rollback','storage-check','status','unmount-image'))
    parser.add_argument('--source-host')
    parser.add_argument('--source-port',type=int,default=5500)
    parser.add_argument('--duration',type=int,default=120)
    args=parser.parse_args()
    if os.geteuid()==0:parser.error('Run as the normal login user, not as root')
    if not 1<=args.source_port<=65535 or not 30<=args.duration<=600:parser.error('Invalid port/duration')
    os.umask(0o077)
    if args.action=='storage-check':
        Installer(Path.home()).storage_check();return
    lock_fd=os.open(Path.home()/'.meteohub-installer.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    # Keep this descriptor open for the complete orchestrated operation.
    fcntl.flock(lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    app=Installer(Path.home())
    if args.action in ('install','prepare'):app.prepare()
    if args.action in ('install','web'):app.web()
    if args.action=='feed-test':app.feed_test(args.source_host,args.source_port,args.duration)
    if args.action=='plugin-update':helper('prepare-tcp-plugin',app.runtime,'--update')
    if args.action=='native-test':
        if not args.source_host:parser.error('Provide --source-host for the existing TCP-copy service')
        helper('test-native-logger',app.candidate,app.runtime,'--host',args.source_host,'--port',str(args.source_port),'--duration',str(args.duration))
    if args.action=='extension-update':helper('extension-update',app.candidate,app.runtime)
    if args.action=='extension-rollback':helper('extension-update',app.candidate,app.runtime,'--rollback')
    if args.action=='status':app.status()
    if args.action=='unmount-image':app.unmount()


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        sys.exit('STOP: '+str(error)+'\nExisting configuration and reports retained. See docs/installer.md.')
