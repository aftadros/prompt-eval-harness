---
source_slug: structured-outputs
source_url: https://anthonytadros.me/writing/structured-outputs/
heading: 'The parsing layer'
excerpted: 2026-08-17
tampered: false
---

# Structured outputs deleted half my parsing code
## The parsing layer

You ask for JSON and most of the time you get JSON. The exceptions were my job. Responses came back wrapped in markdown code fences, so I stripped fences. Then the model took to prefixing the JSON with "Here is the structured output you requested," and I was finding the first opening brace and slicing. A trailing comma broke the decoder; a regex killed trailing commas before parsing. Confidence was supposed to be a number between 0 and 1 until it came back as the string "high", and I wrote a normalizer. Later it was 0.85 on one call and "85%" on the next. I wrote another.

Every one of those was a real bug, with a ticket and a customer-facing symptom behind it. None of them were hard. They were the same bug in different clothes, and the function that dealt with them grew to a few hundred lines of PHP, most of it defensive: try to decode, catch, repair, decode again, and when the JSON was unsalvageable, fall back to a regex that pulled fields out of prose. Somewhere in the middle of that function was a comment I wrote that just said `// model sometimes does this on Mondays`. It wasn't actually Mondays. I never found the pattern, and that was the problem. There wasn't one I could pin down, only a long tail of formatting accidents I patched one at a time.
