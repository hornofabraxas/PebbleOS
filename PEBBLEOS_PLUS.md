# PebbleOS+ (Pebble Time 2 / obelix@pvt)

A thin, low-maintenance fork of [coredevices/PebbleOS](https://github.com/coredevices/pebbleos)
for the Pebble Time 2 (`obelix@pvt`). It carries a small set of quality-of-life
changes and rebuilds automatically when upstream ships a new release.

Upstream is the source of truth. Every change is scoped to stay easy to rebase
and easy to retire once upstream ships an equivalent.

## What it changes

1. **Honor the iPhone silent flag (always-on).** When iOS delivers a
   notification silently because a Focus/Do-Not-Disturb is active (e.g. Sleep
   Focus), the watch stays quiet instead of buzzing. The notification still
   lands in the timeline; only the vibe/backlight alert is suppressed. Carries
   upstream PR #1772 minus its companion-synced preference, defaulted on. No
   companion app or toggle. iOS only (ANCS); Android is unchanged.

2. **Show battery percentage while charging.** The charging modal shows the
   exact percentage. Carries upstream PR #1553 verbatim.

## How you get the firmware

Firmware is delivered as a **GitHub Release**, and only ever published after the
full pipeline passes:

- build both `obelix@pvt` slots and merge into one installable `.pbz`
- run the unit suite (includes the silent-flag and battery-percent tests)
- **boot the build in the QEMU emulator (headless) and confirm it reaches a
  rendered UI with no fault** — if this fails, no firmware is published

On success, a release named `vX.Y.Z-plus` is published (matching the upstream
version it was built from) with `normal_obelix_pvt_vX.Y.Z-plus.pbz` attached.
Install that `.pbz` through the Pebble mobile app.

To be notified: watch this repo with **Custom -> Releases**.

Public repo, so GitHub-hosted Actions minutes are free.

## Automatic rebuilds on upstream releases

`sync-upstream.yml` polls upstream every few hours. When a new upstream
*release* appears that has not been built yet, it rebases the feature commits
onto that release tag and dispatches the build pipeline, which publishes a fresh
`vX.Y.Z-plus` release on success. A rebase conflict fails the run (the signal to
reconcile manually).

## Upstream-drift watchdog

The `watchdog` job checks the carried PRs (#1772, #1553) on every run. If either
is **merged** upstream, the job fails on purpose: reconcile or drop the carried
patch. A soft keyword scan warns if a differently-numbered upstream PR looks
like a reimplementation.

## Recovery (if a build misbehaves on the watch)

These changes only touch the normal application firmware, never the bootloader
or PRF, so a bad application firmware is recoverable, not a brick:

1. It usually self-recovers to PRF after a couple of failed boots.
2. Force recovery with the button combo at power-on if needed.
3. Reflash a known-good `.pbz` from PRF via the mobile app.

Keep a known-good stock `.pbz` for `obelix@pvt` on hand before flashing.
