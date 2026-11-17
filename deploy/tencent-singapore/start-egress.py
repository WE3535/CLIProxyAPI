#!/usr/bin/env python3
import fcntl, os, pathlib, socket, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parent
BINARY = ROOT / "mihomo"
def ready():
    try:
        with socket.create_connection(("127.0.0.1",17897),1): return True
    except OSError: return False
if "--watch" not in sys.argv:
    with open(ROOT / "supervisor.log","ab",buffering=0) as log:
        subprocess.Popen([sys.executable,str(pathlib.Path(__file__).resolve()),"--watch"],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    for _ in range(50):
        if ready(): sys.exit(0)
        time.sleep(.2)
    sys.exit("Gemini egress did not become ready")
lock = open(ROOT / "supervisor.lock","w")
try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError: sys.exit(0)
(ROOT / "supervisor.pid").write_text(str(os.getpid()))
while True:
    if ready():
        time.sleep(5)
        continue
    with open(ROOT / "proxy.log","ab",buffering=0) as log:
        child=subprocess.Popen([str(BINARY),"-d",str(ROOT),"-f",str(ROOT/"config.yaml")],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        (ROOT / "proxy.pid").write_text(str(child.pid))
        child.wait()
    time.sleep(3)
