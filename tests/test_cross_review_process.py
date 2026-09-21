import ctypes
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

MODULE = pathlib.Path(__file__).parents[1] / "subagents" / "scripts" / "claude_cross_review.py"
spec = importlib.util.spec_from_file_location("claude_cross_review_process", MODULE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def process_exited(pid: int) -> bool:
    if os.name != "nt":
        return not pathlib.Path(f"/proc/{pid}").exists()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return True
    try:
        exit_code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise OSError(ctypes.get_last_error(), "GetExitCodeProcess failed")
        return exit_code.value != 259  # STILL_ACTIVE
    finally:
        kernel.CloseHandle(handle)


class ReviewProcessTests(unittest.TestCase):
    def launch_parent(self, directory: pathlib.Path, exit_parent: bool):
        pid_file = directory / "child.pid"
        child_code = "import time; time.sleep(60)"
        parent_code = (
            "import pathlib,subprocess,sys,time; "
            "child=subprocess.Popen([sys.executable, '-c', " + repr(child_code) + "]); "
            "pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8'); "
            + ("time.sleep(0.2)" if exit_parent else "time.sleep(60)")
        )
        process = review.start_review_process([sys.executable, "-c", parent_code, str(pid_file)], directory)
        for _ in range(50):
            if pid_file.exists():
                return process, int(pid_file.read_text(encoding="utf-8"))
            time.sleep(0.05)
        self.fail("parent did not record child pid")

    def wait_exited(self, pid: int):
        for _ in range(50):
            if process_exited(pid):
                return
            time.sleep(0.05)
        self.fail(f"owned child process {pid} survived cleanup")

    def test_owned_active_parent_and_child_are_terminated(self):
        with tempfile.TemporaryDirectory() as temporary:
            process, child_pid = self.launch_parent(pathlib.Path(temporary), exit_parent=False)
            review.terminate(process)
            self.assertIsNotNone(process.poll())
            process.communicate(timeout=2)
            self.wait_exited(child_pid)

    def test_owned_child_dies_when_parent_exits_before_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            process, child_pid = self.launch_parent(pathlib.Path(temporary), exit_parent=True)
            process.wait(timeout=3)
            review.close_review_job(process)
            process.communicate(timeout=2)
            self.wait_exited(child_pid)


if __name__ == "__main__":
    unittest.main()
