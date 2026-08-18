---
source_slug: prompt-injection-is-untrusted-input
source_url: https://anthonytadros.me/writing/prompt-injection-is-untrusted-input/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# Prompt injection is just untrusted input
## Opening

Before I worked on an AI knowledge assistant, I spent two years pulling Social Security numbers off university computers. The job was simple to describe and tedious to do: scan machines for sensitive files, index the hits, and remediate any personally identifiable information that shouldn't be sitting on a lab desktop. What stayed with me wasn't anything about PII. A file is just bytes until something decides to act on it, and the moment you treat content as a command, you've handed control to whoever wrote it.

That's the whole of prompt injection. It gets described as a new attack class that arrived with large language models, and it isn't one. An LLM reads a blob of text where some of the text is data you wanted summarized and some of it is an instruction the model decides to follow, and it has no reliable way to tell which is which. Neither did the PHP apps I was patching years ago when they concatenated a query string straight into a SQL statement.
