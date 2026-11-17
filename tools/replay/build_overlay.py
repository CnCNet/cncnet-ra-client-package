"""Build the native replay game overlay from a local ra-patches checkout.

The pristine input is read from the package's known base Git object, so this also
works after package/ra95.dat has already been replaced by the replay build.
Never downloads an executable or writes over the checked-out package in place.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PACKAGE_BASE = "cab197416e7d4934d548419496d99918a7a3886a"
ORIGINAL_SHA256 = "3d9eef850b9d59191330d3dc4a60ca1a1741663d62bf4c817f1203db813af60e"
ROOT = Path(__file__).resolve().parents[2]


def build(patches, output, original=None, trace=False):
    patches, output = Path(patches).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a new overlay output directory")
    source = (Path(original).read_bytes() if original else subprocess.check_output([
        "git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT),
        "show", PACKAGE_BASE + ":package/ra95.dat"]))
    if hashlib.sha256(source).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("The original game does not match the supported package binary")
    revision = subprocess.check_output([
        "git", "-c", f"safe.directory={patches.as_posix()}", "-C", str(patches),
        "rev-parse", "HEAD"]).decode().strip()
    dirty = subprocess.check_output([
        "git", "-c", f"safe.directory={patches.as_posix()}", "-C", str(patches),
        "status", "--porcelain"]).decode().strip()
    if dirty:
        raise ValueError("Commit the ra-patches source first so the overlay has a reproducible revision")
    with tempfile.TemporaryDirectory(prefix="ra-replay-overlay-") as temporary:
        work = Path(temporary)
        pristine = work / "original.dat"
        pristine.write_bytes(source)
        binary = work / "ra95.dat"
        command = [sys.executable, str(patches / "tools/replay/build_test_binary.py"),
                   str(pristine), str(binary)]
        if trace:
            command.append("--trace")
        subprocess.run(command, check=True)
        manifest_path = binary.with_suffix(".dat.json")
        manifest = json.loads(manifest_path.read_text())
        manifest["replay_source_revision"] = revision
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        (output / "Resources").mkdir(parents=True)
        for name in ("ra95.dat", "ra95.dat.json"):
            shutil.copy2(work / name, output / name)
        shutil.copy2(patches / "tools/replay/GameLoadingWindow.ini", output / "Resources/GameLoadingWindow.ini")
    print(f"Replay overlay ready: {output}; source {revision}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ra-patches", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--original-game", type=Path, help="optional pristine binary instead of the base Git object")
    parser.add_argument("--trace", action="store_true", help="also write development trace files; state checks are always included")
    args = parser.parse_args()
    build(args.ra_patches, args.out, args.original_game, args.trace)
