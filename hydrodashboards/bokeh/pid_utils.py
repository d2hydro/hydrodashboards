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


def terminate_bokeh(ports: list) -> bool:
    # get all pids associated with list of ports
    port_pids = list(
        set([i.pid for i in psutil.net_connections() if i.laddr.port in ports])
    )
    pids = []

    for process in psutil.process_iter():
        # process should have name bokeh.exe
        if process.name() == "bokeh.exe":
            # check if the python-process is associated with the port
            child_processes = process.children(recursive=True)
            child_processes_pids = [i.pid for i in child_processes]

            # if a sub_process_pid is in port_pids we are to terminate that process
            if any((i in port_pids for i in child_processes_pids)):
                # update all to be terminated processes
                pids += [process.pid] + child_processes_pids

                # terminate bokeh
                process.terminate()

                # terminate child-processes
                for process in child_processes:
                    process.terminate()

    return all((not running(i) for i in pids))
