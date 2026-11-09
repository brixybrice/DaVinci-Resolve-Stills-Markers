# Self-check for the duplicate-still retry. Runs without Resolve:
#   python3 tests/test_grab_still_checked.py
# The script talks to Resolve at import time, so the two functions are pulled out with ast.
import ast, os

SRC = os.path.join(os.path.dirname(__file__), "..", "Stills_Markers_python.py")
tree = ast.parse(open(SRC, encoding="utf-8").read())
funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("_wait_for_playhead", "grab_still_checked")]


class FakeTime:
    t = 0.0
    def time(self): return self.t
    def sleep(self, s): self.t += s


ns = {"time": FakeTime(), "_still_fingerprint": None}
exec(compile(ast.Module(body=funcs, type_ignores=[]), SRC, "exec"), ns)
grab = ns["grab_still_checked"]


class Fake:
    """Timeline + album + gallery in one. `frames` is what each successive GrabStill shows."""
    def __init__(self, frames):
        self.frames, self.deleted, self.n = list(frames), [], 0
    def GetCurrentTimecode(self): return "01:00:00:10"
    def SetCurrentTimecode(self, tc): return True
    def SetCurrentStillAlbum(self, a): return True
    def GrabStill(self):
        self.n += 1
        return (self.n, self.frames.pop(0))
    def DeleteStills(self, stills): self.deleted += stills


fp = lambda album, still: still[1]

# 1. Viewer late once: first grab repeats previous frame, retry gets the right one.
f = Fake(["A", "B"])
still, new_fp, suspect = grab(f, f, f, "01:00:00:10", "A", fingerprint=fp)
assert new_fp == "B" and not suspect and f.deleted == [(1, "A")], (still, f.deleted)

# 2. Truly identical frame: 3 retries, last still kept and flagged, the 3 earlier ones deleted.
f = Fake(["A"] * 4)
still, new_fp, suspect = grab(f, f, f, "01:00:00:10", "A", fingerprint=fp)
assert suspect and still == (4, "A") and len(f.deleted) == 3

# 3. First marker (no previous) and failed fingerprint: no comparison, no retry.
f = Fake(["A"]); assert grab(f, f, f, "01:00:00:10", None, fingerprint=fp)[2] is False and not f.deleted
f = Fake(["A"]); assert grab(f, f, f, "01:00:00:10", "A", fingerprint=lambda a, s: None)[2] is False

# 4. Grab failure passes through as None so the script can show its Gallery alert.
class Fail(Fake):
    def GrabStill(self): return None
f = Fail([]); assert grab(f, f, f, "01:00:00:10", "A", fingerprint=fp)[0] is None

print("ok")
