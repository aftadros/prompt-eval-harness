# prompts

The artifact under test, versioned as plain files so a change is a diff.

- **`v1.txt`** is P_A, the grounded-QA baseline.
- **`v2.txt`** is P_B, identical to P_A except for rule 3, which gains the "be
  more forthcoming / avoid unnecessary refusals" edit.

P_B is not a strawman and it is not neutral either, so it is worth being explicit
about what it is. It reproduces the edit from *How to tell if a prompt change
actually helped*: the kind of change that reads as an obvious improvement, tests
well on the questions you happen to type, and plausibly erodes refusal behavior on
the questions you do not. Choosing an edit that might produce that pattern is a
legitimate way to demonstrate the method. Whether it actually produces it is the
experiment, and the answer is in `runs/`, not here.

Diff them:

```
diff prompts/v1.txt prompts/v2.txt
```
