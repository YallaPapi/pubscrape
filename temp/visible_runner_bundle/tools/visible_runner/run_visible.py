#!/usr/bin/env python3
"""
run_visible.py — Make hidden/background runs visible.
Usage:
  python run_visible.py -- <command> [args...]
  python run_visible.py --timeout 600 --env FOO=bar -- python -u your_script.py arg1

What it does:
- Forces unbuffered output from Python children.
- Streams stdout/stderr live to your console.
- Tees to logs/latest.log and logs/events-*.jsonl with timestamps.
- Exits with the same return code as the child process.
"""
import argparse, os, sys, subprocess, time, json, pathlib, shlex, datetime

def parse_kv(s: str):
    if "=" not in s:
        raise argparse.ArgumentTypeError("ENV must be in KEY=VALUE form")
    k, v = s.split("=", 1)
    return k, v

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--env", action="append", type=parse_kv, default=[],
                        help="Additional env vars: --env KEY=VALUE (repeatable)")
    parser.add_argument("--cwd", default=None, help="Working directory to run the command in")
    parser.add_argument("--help", action="store_true")
    parser.add_argument("dashdash", nargs="?", default=None)  # should be '--'
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.help or args.dashdash != "--" or not args.cmd:
        print(__doc__.strip())
        sys.exit(2)

    # Logs setup
    root = pathlib.Path(__file__).resolve().parent
    logs_dir = (root / "logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_txt = logs_dir / f"run-{ts}.log"
    events_jsonl = logs_dir / f"events-{ts}.jsonl"
    latest_symlink = logs_dir / "latest.log"
    # Best effort to update "latest.log"
    try:
        if latest_symlink.exists() or latest_symlink.is_symlink():
            latest_symlink.unlink()
        latest_symlink.symlink_to(log_txt.name)
    except Exception:
        # On Windows, symlinks may fail; fall back to copying at end
        pass

    # Child env
    env = os.environ.copy()
    # Force unbuffered Python children
    env["PYTHONUNBUFFERED"] = "1"
    # Also disable output buffering in many C stdio programs
    env["STDOUT_LINE_BUFFERED"] = "1"
    for k, v in args.env:
        env[k] = v

    # Command
    cmd_list = args.cmd
    # On Windows, recommend shell=False; we'll pass list
    shell = False

    # Open files
    log_f = open(log_txt, "a", encoding="utf-8", buffering=1)
    ev_f = open(events_jsonl, "a", encoding="utf-8", buffering=1)

    def emit_event(kind, data):
        ev = {
            "ts": time.time(),
            "kind": kind,
            "data": data,
        }
        ev_f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    emit_event("start", {
        "cmd": cmd_list,
        "cwd": args.cwd or os.getcwd(),
        "timeout": args.timeout,
        "env_added": {k: v for k, v in args.env},
    })

    start = time.time()
    # Start process
    try:
        p = subprocess.Popen(
            cmd_list,
            cwd=args.cwd or None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
        )
    except FileNotFoundError as e:
        msg = f"[launcher] Command not found: {cmd_list[0]}"
        print(msg, file=sys.stderr, flush=True)
        log_f.write(msg + "\n")
        emit_event("error", {"message": msg})
        sys.exit(127)

    # Non-blocking read loop
    import selectors
    sel = selectors.DefaultSelector()
    sel.register(p.stdout, selectors.EVENT_READ)
    sel.register(p.stderr, selectors.EVENT_READ)

    def stamp():
        return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

    try:
        while True:
            if args.timeout and (time.time() - start) > args.timeout:
                p.kill()
                emit_event("timeout", {"seconds": args.timeout})
                print(f"[{stamp()}] ⏰ TIMEOUT after {args.timeout}s — process killed", flush=True)
                log_f.write(f"[{stamp()}] TIMEOUT after {args.timeout}s — process killed\n")
                break

            if p.poll() is not None and not sel.get_key(p.stdout).fileobj.readable() and not sel.get_key(p.stderr).fileobj.readable():
                # process ended; we'll drain in the loop below
                pass

            events = sel.select(timeout=0.1)
            if not events and p.poll() is not None:
                # nothing left and process exited
                break

            for key, _ in events:
                line = key.fileobj.readline()
                if not line:
                    continue
                stream = "STDOUT" if key.fileobj is p.stdout else "STDERR"
                line_no_nl = line.rstrip("\n")
                out = f"[{stamp()}] {stream} | {line_no_nl}"
                print(out, flush=True)
                log_f.write(out + "\n")
                emit_event("line", {"stream": stream, "text": line_no_nl})

        rc = p.wait()
        emit_event("exit", {"returncode": rc, "elapsed_sec": round(time.time() - start, 3)})
        print(f"[{stamp()}] EXIT {rc}", flush=True)
        log_f.write(f"[{stamp()}] EXIT {rc}\n")

    finally:
        log_f.flush(); ev_f.flush()
        log_f.close(); ev_f.close()
        # On Windows, maintain latest.log by copying
        try:
            if not latest_symlink.exists():
                import shutil
                shutil.copyfile(log_txt, logs_dir / "latest.log")
        except Exception:
            pass

    sys.exit(rc if isinstance(rc, int) else 1)

if __name__ == "__main__":
    main()
