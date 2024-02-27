import psutil
import json
from pathlib import Path


def _result(pid, create_timestamp=None):
    result = {"pid": pid}
    if create_timestamp is not None:
        result["create_timestamp"] = create_timestamp
    return result


def get() -> dict:
    """Get the pid and time-stamp of the current process."""
    pid = psutil.Process().pid
    create_timestamp = psutil.Process(pid).create_time()
    return {"pid": pid, "create_timestamp": create_timestamp}


def write_pid_file(file_path: str, pid: int, create_timestamp=None):
    result = _result(pid, create_timestamp)
    # write result
    path = Path(file_path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    else:
        if path.exists():
            path.unlink(missing_ok=True)
    path.write_text(f"{json.dumps(result)}")


def write(file_path: str) -> dict:
    """Write and return pid of current python process."""
    result = get()
    write_pid_file(file_path, **result)

    return result


def read(file_path: str) -> dict:
    """Read the process from a file."""
    path = Path(file_path)
    if path.exists():
        result = json.loads(path.read_text())
    else:
        result = None
    return result


def running(pid: int, create_timestamp=None) -> bool:
    """Check if a Python-process is running by Windows PID."""
    exists = False

    try:
        process = psutil.Process(pid)
        if process.name() == "python.exe":
            if create_timestamp is not None:
                if create_timestamp == process.create_time():
                    exists = True
            else:
                exists = True
    except psutil.NoSuchProcess:
        pass

    return exists


def terminate(pid: int, create_timestamp=None) -> bool:
    terminated = False

    if running(pid, create_timestamp):
        try:
            process = psutil.Process(pid)
            process.terminate()
            terminated = running(pid)
        except psutil.NoSuchProcess:
            pass

    return terminated


def terminate_bokeh() -> bool:
    pids = []
    for process in psutil.process_iter():
        if process.name() == "bokeh.exe":
            pids += [process.pid]
            process.terminate()
    return all((not running(i) for i in pids))
