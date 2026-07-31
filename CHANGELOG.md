# Changelog

All notable release changes are recorded here. Dates and publication status
must be read from Git/GitHub; a source entry does not itself prove publication.

## [Unreleased]

- The source Release Manifest remains `unreleased / public=false` until a
  release artifact receives an injected and verified public identity.
- Added release-truth, licensing, third-party, and security documentation.
- Added a post-publication gate that reads back the exact public asset set,
  provider digests, release identity, and downloaded SHA-256 payloads.

## [0.4.0] - historical release

`v0.4.0` is retained as historical publication evidence. Readback found
incomplete checksum payload coverage: the public installer name did not match
its checksum-manifest name and an extra public payload was absent from the
manifest. The tag, Release, and assets are intentionally preserved; remediation
must use a new version. This entry makes no signature claim.
