#!/bin/bash
# Initial offline-consistent runtime backup, before installing RAM mounts.
# Usage: sudo bash tools/bootstrap-persist.sh RUNTIME PERSIST_MOUNT UUID
set -euo pipefail
umask 077
export LC_ALL=C

runtime=${1:?Runtime directory required}
persist=${2:?Persistence mount required}
uuid=${3:?Expected filesystem UUID required}
test "$#" = 3
test "$(id -u)" = 0
test "$(readlink -f "$runtime")" = "$runtime"
test "$(readlink -f "$persist")" = "$persist"
test "$runtime" != /
test "$persist" != /
test "$(findmnt -nro UUID --mountpoint "$persist")" = "$uuid"
findmnt -nro OPTIONS --mountpoint "$persist" | grep -Eq '(^|,)ro(,|$)'
test -f "$runtime/live-install.json"
test -f "$runtime/root/home/meteohub/meteohub.conf"
test -f "$runtime/root/data/dashboard/weather.sqlite"
test -d "$runtime/root/data/weather"
test ! -L "$persist/snapshots"
# This first backup must not silently omit nested RAM/bind mounts.
if findmnt -rn -o TARGET | awk -v p="$runtime" '$0==p || index($0,p "/")==1 {f=1} END {exit !f}'; then
    echo 'STOP: Runtime already has mounts; bootstrap is only for the initial SD runtime.' >&2
    exit 1
fi
need=$(( $(du -sx --apparent-size -B1 "$runtime" | cut -f1) + 67108864 ))
test "$(df -B1 --output=avail "$persist" | tail -n 1)" -gt "$need"
test "$(df -B1 --output=avail /root | tail -n 1)" -gt "$need"
exec 9>/run/lock/meteohub-storage.lock
flock -n 9
exec 8>"$runtime/.feed-consumer.lock"
units=(meteohub-web-test.socket meteohub-web-test.service meteohub-live-logger.service meteohub-dashboard-index.service)
for unit in "${units[@]}"; do systemctl is-active --quiet "$unit"; done

paused=0
writable=0
complete=''
cleanup() {
    result=$?
    trap - EXIT
    set +e
    if test "$writable" = 1; then
        sync -f "$persist" || result=1
        mount -o remount,ro "$persist" || result=1
    fi
    flock -u 8
    if test "$paused" = 1; then
        systemctl start "${units[@]}" || result=1
        for unit in "${units[@]}"; do systemctl is-active --quiet "$unit" || result=1; done
    fi
    if test "$result" = 0; then
        printf 'VERIFIED BACKUP: %s\nServices active again; new weather recording still needs checking.\n' "$complete"
    else
        echo 'STOP: backup/cleanup failed; inspect output, mount and services. Partial files retained.' >&2
    fi
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

writable=1
mount -o remount,rw "$persist"
install -d -m 0700 "$persist/snapshots"
snapshot=$(mktemp -d "$persist/snapshots/.pending-XXXXXXXX")
restore=$(mktemp -d /root/meteohub-restore-check-XXXXXXXX)
printf 'Preparation: %s\nRestore check: %s\n' "$snapshot" "$restore"

paused=1
systemctl stop "${units[@]}"
for unit in "${units[@]}"; do test "$(systemctl show "$unit" -p ActiveState --value)" = inactive; done
test "$(systemctl show meteohub-live-logger.service -p Result --value)" = success
flock -n 8
test -z "$(find "$runtime" -xdev ! -type d ! -type f ! -type l -print -quit)"

tar --one-file-system --acls --xattrs --numeric-owner -cpf "$snapshot/runtime.tar" -C "$runtime" .
tar --acls --xattrs --compare -f "$snapshot/runtime.tar" -C "$runtime"
(cd "$snapshot"; sha256sum runtime.tar > SHA256SUMS; sha256sum -c SHA256SUMS)
tar --acls --xattrs --numeric-owner -xpf "$snapshot/runtime.tar" -C "$restore"
tar --acls --xattrs --compare -f "$snapshot/runtime.tar" -C "$restore"
python3 -c 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); r=c.execute("PRAGMA integrity_check").fetchall(); c.close(); assert r==[("ok",)],r; print("SQLite restore: OK")' "$restore/root/data/dashboard/weather.sqlite"
printf 'schema=1\nruntime=%s\nfilesystem_uuid=%s\ncreated_utc=%s\n' "$runtime" "$uuid" "$(date -u +%FT%TZ)" > "$snapshot/verified.txt"
sync -f "$persist"
complete="$persist/snapshots/initial-${snapshot##*.pending-}"
test ! -e "$complete"
mv -T "$snapshot" "$complete"
sync -f "$persist"
rm -rf -- "$restore"
