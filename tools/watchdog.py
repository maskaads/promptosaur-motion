#!/usr/bin/env python3
"""Run a render and restart it when it freezes.

A render that hangs looks the same as a slow one until you look at its
output. This wrapper watches a folder of frames (or a file) and kills the
render when nothing new has been written for --stall seconds, then starts it
again. Pair it with a renderer that skips frames that already exist
(capture.mjs does), and a restart costs only the frames that were lost.

Usage:
  python watchdog.py --watch frames [--stall 120] [--retries 3] -- node capture.mjs page.html --duration 15
  python watchdog.py --watch out.mp4 --stall 300 -- blender -b scene.blend -a

Exit code: the render's own code when it finishes, 2 when it froze more
than --retries times.
"""
import argparse
import os
import signal
import subprocess
import sys
import time


def newest_change(path):
    """Latest modification time and total size under path (file or folder)."""
    if not os.path.exists(path):
        return 0.0, 0
    if os.path.isfile(path):
        st = os.stat(path)
        return st.st_mtime, st.st_size
    latest, size = 0.0, 0
    with os.scandir(path) as it:
        for e in it:
            if e.is_file():
                st = e.stat()
                latest = max(latest, st.st_mtime)
                size += st.st_size
    return latest, size


def kill_tree(p):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, creationflags=0x08000000)
    else:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--watch", required=True, help="folder of frames or output file to watch")
    ap.add_argument("--stall", type=float, default=120, help="seconds without new output that count as frozen")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--grace", type=float, default=180, help="seconds allowed before the first output appears")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        sys.exit("give the render command after --")

    for attempt in range(a.retries + 1):
        # own process group so the whole render tree can be stopped; no console window on Windows
        kw = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000} if os.name == "nt"
              else {"start_new_session": True})
        p = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, **kw)
        started = time.time()
        last_state = newest_change(a.watch)
        last_change = started
        froze = False
        while p.poll() is None:
            time.sleep(2)
            state = newest_change(a.watch)
            if state != last_state:
                last_state, last_change = state, time.time()
            limit = a.grace if last_change == started else a.stall
            if time.time() - last_change > limit:
                print(f"[watchdog] no new output in {a.watch} for {time.time() - last_change:.0f} s; stopping the render",
                      flush=True)
                kill_tree(p)
                p.wait()
                froze = True
                break
        if not froze:
            print(f"[watchdog] render finished with code {p.returncode} after {time.time() - started:.0f} s", flush=True)
            sys.exit(p.returncode)
        if attempt < a.retries:
            print(f"[watchdog] restart {attempt + 1} of {a.retries}", flush=True)
    print(f"[watchdog] the render froze {a.retries + 1} times; look at its log before trying again", flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
