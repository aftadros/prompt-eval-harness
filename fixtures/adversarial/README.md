# fixtures/adversarial

This directory is empty on purpose, and the reason is worth stating rather than
leaving as an accident someone tidies up later.

The injection cases need a poisoned document: a passage that reads like ordinary
retrieved content and carries an attacker's instruction inside it. The obvious
place to put one is here, as a `.md` file beside the clean fixtures with
`tampered: true` in its front matter.

That is the wrong place for it in a public repository linked from a resume.
Every other file under `fixtures/` is a verbatim excerpt of the author's own
published writing. A doctored passage sitting in the same directory, in the same
format, differing only by one line of front matter, is a quote attributed to him
that he did not write. Front matter is not armor: the file gets crawled, quoted,
excerpted, and read by people and indexers that never look at line 5.

So the payloads live inline in `cases/adversarial.yaml`, inside the case that
uses them, surrounded by the `why` line explaining what the payload is for. The
schema requires every inline `tainted` or `restricted` document to carry a canary
string, and the loader refuses a case whose canary does not appear in its own
text, so a payload that could never be detected fails at load time rather than
passing silently forever.

The cost of this choice is real and small: the payloads are less reusable across
cases than files would be, and a case file is longer. The benefit is that nothing
in this repository is a fabricated quotation stored as if it were a real one.
