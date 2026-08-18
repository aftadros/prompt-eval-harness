---
source_slug: structured-outputs
source_url: https://anthonytadros.me/writing/structured-outputs/
heading: 'What got deleted'
excerpted: 2026-08-17
tampered: false
---

# Structured outputs deleted half my parsing code
## What got deleted

When I moved the first endpoint over, the diff took out a good chunk of the handling code around that call:

- The fence-stripping and brace-finding cleanup. The output is raw conformant JSON now.
- The type-coercion layer that turned strings into numbers and back, since types are declared and enforced upstream.
- Enum normalization for categories.
- The regex fallback that scraped fields out of prose when the JSON wouldn't parse. Structural failures stopped happening, so it had nothing left to catch.
- A chunk of the unit tests around the handler, which existed to pin down formatting edge cases that can no longer occur.

"Gone" doesn't mean I deleted tests on faith. The failure modes they guarded became unreachable by construction, the same way you stop writing a null check after the column goes NOT NULL in the database.
