# Upstream provenance

- Source: https://github.com/DeliciousBuding/xiaohongshu-skill
- Revision: `afa96802d3e61cdd5e7bd7b37ec59182bbe07d37`
- Version: 1.5.1
- Imported: 2026-10-08
- Maintained in: https://github.com/chrisopal/skills/tree/main/xiaohongshu-skill
- License: Apache-2.0; original LICENSE and THIRD_PARTY_NOTICES.md retained.

The initial import preserves tracked upstream files byte-for-byte. This is a
vendored fork in the existing skills collection, not a GitHub fork-network
relationship. Local adaptations are separate commits following this baseline.
Do not include account sessions, cookies, media files, or publication records.

## Local adaptations

- Manifest-based video preparation, media validation and profile-local job ledger.
- Exact body/tag readback, custom cover verification and saved-draft recovery.
- Bounded upload readiness checks; local and remote video preview evidence separated.
- Content-based duplicate protection, including manual publication and uncertain submission.
- Offline Chromium fixtures and root-repository CI; no live public submission tests.

No production dependencies added. Browser-account data remains outside the skill.
