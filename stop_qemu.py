#!/usr/bin/python3
"""Request guest poweroff through QEMU HMP, then wait for QEMU to exit."""
import os,pathlib,socket,sys,time

def main():
 if len(sys.argv)!=3:raise SystemExit('Usage: stop_qemu.py MONITOR_SOCKET MAINPID')
 monitor,pid=sys.argv[1],int(sys.argv[2])
 if pid<=1:raise SystemExit('Invalid QEMU PID')
 try:
  command=pathlib.Path('/proc',str(pid),'comm').read_text().strip()
 except FileNotFoundError:return
 if not command.startswith('qemu-system-'):raise SystemExit('Refusing non-QEMU process')
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
  sock.settimeout(5);sock.connect(monitor);sock.recv(8192)
  sock.sendall(b'system_powerdown\n')
 print('Guest poweroff requested',flush=True)
 deadline=time.monotonic()+90
 while time.monotonic()<deadline:
  try:os.kill(pid,0)
  except ProcessLookupError:
   print('QEMU exited after guest poweroff',flush=True);return
  time.sleep(.5)
 raise SystemExit('Guest did not exit within 90 seconds; inspect console before further action')
if __name__=='__main__':main()
