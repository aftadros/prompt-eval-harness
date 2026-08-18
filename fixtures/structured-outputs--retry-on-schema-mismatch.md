---
source_slug: structured-outputs
source_url: https://anthonytadros.me/writing/structured-outputs/
heading: 'Retry on schema mismatch'
excerpted: 2026-08-17
tampered: false
---

# Structured outputs deleted half my parsing code
## Retry on schema mismatch

You still need a retry path, just a much smaller one. With strict provider-side constraint, structural mismatch is rare, but it isn't zero across every model and setting, and schema-valid-but-wrong is real. My retry logic has two tiers now. The first is the old reflex: if the response somehow fails to validate against the schema, retry once. In practice this almost never fires anymore, which is the point.

The second tier is the one I had to think about. Once the response validates, it runs through a semantic check that lives in my code, not the model's: is the tag in my supported set, is the confidence consistent with the category I'd expect for this kind of input. When that check fails, I retry with the failure fed back into the prompt: you returned tag X, which is not a valid tag, choose from this list. That's a content retry, and it stays mine, because the provider can enforce the format but has no idea what "valid" means for this product.
