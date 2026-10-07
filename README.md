# PebbleOS+ upstream changelogs

This branch holds one plain-language changelog per upstream PebbleOS release
(`changelogs/<tag>.md`). They are written by an hourly Claude routine from the
upstream commit messages and shown at the top of the matching `vX.Y.Z-plus`
release on this fork. It is separate from `pebbleos-plus` because that branch is
rebased and force-pushed on every upstream release. The `claude/` prefix is
because Claude cloud sessions may only push to `claude/` branches, which also
keeps the routine away from `pebbleos-plus` (a push there publishes firmware).

- `tools/changelog.py todo` lists the upstream tags that still need a
  changelog, each marked `mainline` (the newest vX.Y.Z) or `backport` (an
  older firmware line, which gets no PebbleOS+ build). A tag needs one until
  its file exists here, so a failed run is retried on the next one. Tags created before v4.39.0 are never backfilled.
- `tools/changelog.py log <tag>` prints the commit range to summarize. The
  range starts at the nearest release tag in the tag's own history, not the
  previously created tag: upstream cuts patch releases on release branches.
- `tools/changelog.py write <tag> <body>` checks the text and saves the file.
- `tools/changelog.py apply <tag>` puts the file on the `<tag>-plus` release.
  It runs from `.github/workflows/apply-changelog.yml` when a changelog is
  pushed, and from the PebbleOS+ release job when a release is published.

To fix a changelog by hand, edit its file and push to this branch; the
release notes update on their own. If a changelog and its release ever land
at the same moment and neither side applies it, the weekly PebbleOS+ rebuild
re-applies it, or push any edit to the file.
