"""Track only processes started by this checkout; never kill by port alone."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def ps(pid, column):
    return subprocess.run(['ps', '-ww', '-p', str(pid), '-o', column + '='], capture_output=True, text=True).stdout.strip()


def cwd(pid):
    result = subprocess.run(['lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'], capture_output=True, text=True)
    return next((line[1:] for line in result.stdout.splitlines() if line.startswith('n')), '')


def identity(pid):
    return {'pid': int(pid), 'started': ps(pid, 'lstart'), 'command': ps(pid, 'args')}


def alive(record):
    current = identity(record['pid'])
    return bool(current['started']) and current == {key: record[key] for key in current}


def read_record(file, root):
    try:
        record = json.loads(Path(file).read_text())
        if record['root'] != str(Path(root).resolve()) or not alive(record):
            return None
        Path(cwd(record['pid'])).resolve().relative_to(Path(root).resolve())
        return record
    except (OSError, ValueError, KeyError, TypeError):
        return None


def descendants(pid):
    output = subprocess.run(['ps', '-ax', '-o', 'pid=,ppid='], capture_output=True, text=True).stdout
    edges = [tuple(map(int, line.split())) for line in output.splitlines() if len(line.split()) == 2]
    found = {int(pid)}
    while True:
        more = {child for child, parent in edges if parent in found} - found
        if not more:
            return found
        found.update(more)


def stop(file, root):
    path = Path(file)
    if not path.exists():
        return 0
    record = read_record(file, root)
    if not record:
        print(f'{path.name}: stale or foreign process; no process was signalled')
        return 0
    owned = [identity(pid) for pid in descendants(record['pid'])]
    for candidate in reversed(owned):
        if alive(candidate):
            try:
                os.kill(candidate['pid'], signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and any(alive(item) for item in owned):
        time.sleep(.1)
    for candidate in owned:
        if alive(candidate):
            try:
                os.kill(candidate['pid'], signal.SIGKILL)
            except ProcessLookupError:
                pass
    path.unlink(missing_ok=True)
    print(f'{record["service"]}: managed process tree stopped')
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['record', 'status', 'stop', 'owns-port'])
    parser.add_argument('file')
    parser.add_argument('root')
    parser.add_argument('value', nargs='?')
    parser.add_argument('service', nargs='?')
    args = parser.parse_args()
    if args.operation == 'record':
        record = identity(int(args.value))
        # Shell launchers may immediately exec their real executable. Store
        # the stable command instead of a short-lived bootstrap command.
        for _ in range(20):
            time.sleep(.05)
            current = identity(int(args.value))
            if current == record:
                break
            record = current
        if not record['started']:
            raise RuntimeError('Service exited before its PID could be recorded')
        Path(cwd(record['pid'])).resolve().relative_to(Path(args.root).resolve())
        record.update(root=str(Path(args.root).resolve()), service=args.service)
        path = Path(args.file)
        path.write_text(json.dumps(record))
        path.chmod(0o600)
        return 0
    if args.operation == 'stop':
        return stop(args.file, args.root)
    record = read_record(args.file, args.root)
    if not record:
        return 1
    if args.operation == 'owns-port':
        listeners = subprocess.run(['lsof', '-tiTCP:' + args.value, '-sTCP:LISTEN'], capture_output=True, text=True).stdout.split()
        owned = descendants(record['pid'])
        return 0 if listeners and all(int(pid) in owned for pid in listeners) else 1
    print(record['pid'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
