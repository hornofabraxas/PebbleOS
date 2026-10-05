#!/usr/bin/env python3
"""Refuse firmware the bootloader would rank as a DEV image.

pblboot boots the valid slot with the highest header priority. A tag that is
not an exact release gets the DEV band, which outranks every release, so a
watch that installs one keeps booting it over all later releases until a
recovery boot. The rule itself comes from tools/pblboot.py, not a copy.

  check_boot_priority.py tag TAG            TAG must get the release band
  check_boot_priority.py pbz PBZ FULLVER    both slot headers must be FULLVER
  check_boot_priority.py self-test          exercise the checks above
"""

import io
import json
import struct
import sys
import tempfile
import types
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
try:
    import intelhex  # noqa: F401
except ImportError:
    # pblboot imports IntelHex at module top but boot_priority() never uses it.
    stub = types.ModuleType("intelhex")
    stub.IntelHex = None
    sys.modules["intelhex"] = stub
import pblboot  # noqa: E402

HEADER = struct.Struct("<LLQLLL")


def _release_priority(tag):
    """(priority, error) for tag as the build would stamp it."""
    try:
        prio = pblboot.boot_priority(tag, commit_timestamp=0)
    except ValueError as e:
        return None, f"{tag!r}: {e}"
    if prio >> 56 != pblboot.PRIORITY_BAND_RELEASE:
        return None, (
            f"{tag!r} is not a release tag: pblboot stamps it DEV band "
            f"0x{prio >> 56:02x}, which outranks every release"
        )
    return prio, None


def check_tag(tag):
    _, err = _release_priority(tag)
    return [err] if err else []


def check_pbz(pbz, fullver):
    expected, err = _release_priority(fullver)
    if err:
        return [err]
    errors = []
    with zipfile.ZipFile(pbz) as z:
        names = set(z.namelist())
        for slot in ("slot0", "slot1"):
            binname, manname = f"{slot}/pebbleos.bin", f"{slot}/manifest.json"
            if binname not in names or manname not in names:
                errors.append(f"{slot}: {binname} or {manname} missing from the pbz")
                continue
            with z.open(binname) as f:
                raw = f.read(HEADER.size)
            if len(raw) < HEADER.size:
                errors.append(f"{slot}: pebbleos.bin is shorter than a pblboot header")
                continue
            magic, _, prio, _, _, _ = HEADER.unpack(raw)
            print(f"{slot}: priority=0x{prio:016x} band=0x{prio >> 56:02x}")
            if magic != pblboot.MAGIC:
                errors.append(f"{slot}: bad pblboot header magic 0x{magic:08x}")
            elif prio >> 32 != expected >> 32:
                kind = "DEV band" if prio >> 56 != pblboot.PRIORITY_BAND_RELEASE else "wrong version"
                errors.append(
                    f"{slot}: priority 0x{prio:016x} ({kind}) does not match release "
                    f"{fullver} (want 0x{expected >> 32:08x}xxxxxxxx)"
                )
            try:
                tag = json.loads(z.read(manname))["firmware"]["versionTag"]
            except (ValueError, KeyError, TypeError) as e:
                errors.append(f"{slot}: unreadable manifest versionTag ({e!r})")
                continue
            if tag != fullver:
                errors.append(f"{slot}: manifest versionTag {tag!r} != {fullver!r}")
    return errors


def _fake_pbz(path, prio, tag, slots=("slot0", "slot1"), manifest=None, magic=None, raw=None):
    body = b"\x00" * 64
    with zipfile.ZipFile(path, "w") as z:
        for slot in slots:
            header = HEADER.pack(magic or pblboot.MAGIC, 28, prio, 512, len(body), 0)
            z.writestr(f"{slot}/pebbleos.bin", raw if raw is not None else header + body)
            z.writestr(f"{slot}/manifest.json", manifest or json.dumps({"firmware": {"versionTag": tag}}))


def self_test():
    rel = pblboot.boot_priority("v4.38.4", 1790000000)
    dev = pblboot.boot_priority("v4.37.0-plus")
    older = pblboot.boot_priority("v4.38.3", 1790000000)
    ok = True
    tag_cases = [
        ("v4.38.4", True), ("v4.38.4-rc1", True), ("v4.37.0-plus", False),
        ("v4.37.0-12-g1a2b3c4", False), ("v4.9.142.5", False), ("v4.300.0", False),
    ]
    for tag, want_pass in tag_cases:
        passed = not check_tag(tag)
        ok &= passed == want_pass
        print(f"self-test tag {tag!r}: {'pass' if passed else 'refused'}"
              f"{'' if passed == want_pass else '  <-- WRONG'}")
    with tempfile.TemporaryDirectory() as d:
        pbz_cases = [
            ("release header", dict(prio=rel, tag="v4.38.4"), "v4.38.4", True),
            ("DEV header, DEV tag", dict(prio=dev, tag="v4.37.0-plus"), "v4.37.0-plus", False),
            ("DEV header, release tag", dict(prio=dev, tag="v4.38.4"), "v4.38.4", False),
            ("older release header", dict(prio=older, tag="v4.38.4"), "v4.38.4", False),
            ("manifest versionTag mismatch", dict(prio=rel, tag="v4.38.4-plus"), "v4.38.4", False),
            ("bad header magic", dict(prio=rel, tag="v4.38.4", magic=0xDEADBEEF), "v4.38.4", False),
            ("truncated pebbleos.bin", dict(prio=rel, tag="v4.38.4", raw=b"\x3d\xb8"), "v4.38.4", False),
            ("slot1 missing", dict(prio=rel, tag="v4.38.4", slots=("slot0",)), "v4.38.4", False),
            ("manifest without versionTag", dict(prio=rel, tag="", manifest="{}"), "v4.38.4", False),
        ]
        for i, (name, kw, fullver, want_pass) in enumerate(pbz_cases):
            path = Path(d) / f"{i}.pbz"
            _fake_pbz(path, **kw)
            with io.StringIO() as sink:
                stdout, sys.stdout = sys.stdout, sink
                try:
                    passed = not check_pbz(path, fullver)
                finally:
                    sys.stdout = stdout
            ok &= passed == want_pass
            print(f"self-test pbz {name}: {'pass' if passed else 'refused'}"
                  f"{'' if passed == want_pass else '  <-- WRONG'}")
    return [] if ok else ["self-test failed: the guard no longer behaves as specified"]


def main(argv):
    if argv[:1] == ["tag"] and len(argv) == 2:
        errors = check_tag(argv[1])
    elif argv[:1] == ["pbz"] and len(argv) == 3:
        errors = check_pbz(argv[1], argv[2])
    elif argv == ["self-test"]:
        errors = self_test()
    else:
        print(__doc__, file=sys.stderr)
        return 2
    for e in errors:
        print(f"::error::{e}")
    if not errors:
        print("boot priority check passed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
