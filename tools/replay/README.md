# Native RA1 replay package integration

The patched Westwood game records and plays replay files itself. The client
launches `ra95.dat` directly. There is no replay launcher, temporary game copy,
CLR dependency or client-source change.

This package depends on [CO2's ra-patches contribution](https://github.com/CO2-code/ra-patches/pull/9).
The included manifest records the exact source revision and binary patch audit.
The normal game build includes state checks; `--trace` additionally produces
development trace files.

The existing **Options → Game → Record Replays** setting controls recording.
Watch through **Load Game → Replays → Play**. ClientDefinitions enables replay
support, sets directory `Replays` and extension `.rarp`, and retains the direct
game launcher. File naming, listing, import/delete, pruning and launching use the
existing client. `GameLoadingWindow.ini` hides unimplemented YR viewer controls.

The native viewer retains the recorded house/shroud, free camera and read-only
sidebar. Observer switching, seeking and the advanced YR viewer controls remain
unported. Fresh skirmish and multiplayer are supported; campaigns and resumed
saves continue without recording. Matching engine/assets/rules are required.

## Rebuild

Requirements: Python 3, NASM, 32-bit-capable GCC and GNU ld with i386pe on PATH,
plus the ra-patches replay checkout. No .NET build is involved.

```powershell
python tools/replay/build_overlay.py --ra-patches ../ra-patches --out ../replay-overlay
```

The output directory must be new. The tool reads pristine `ra95.dat` from base
Git object `cab197416e7d4934d548419496d99918a7a3886a`, verifies its SHA-256,
builds in temporary directories and creates the game/manifest/UI overlay. It
does not download binaries or overwrite package/. Fetch the base commit for a
shallow clone, or pass `--original-game <pristine.dat>`.

The game contains separate RX code and RW state sections. Review its manifest,
then copy the overlay into package/. Rebuild after changing ra-patches. The
source checkout must be clean when generating a reviewable release artifact.

The package's original client reader accepts the YRRP metadata envelope while
the game consumes the RA1N-specific body. This is not a YR event stream. The
retired external-launcher RA1R prototype format is not supported. See ra-patches'
`tools/replay/CLIENT-INTEGRATION.md` and `NATIVE-FORMAT.md` for architecture and
limits. `replay-native.log` contains completion, state-check counts and errors.

Windows native builds are exercised locally. Wine/Unix playback and a full legacy
ra-patches rebuild have not been validated. Broader real-network and custom-rule
testing remains necessary before treating the draft contribution as a release.
