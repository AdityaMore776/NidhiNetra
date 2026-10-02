"""Evaluation tooling: a synthetic eSAKSHI corpus with planted, labelled problems, a stats
builder that needs no pandas, and a harness that measures what each engine catches.

Nothing here runs in the live engine. It exists so every engine can be tested on works it
has never seen, in many random districts, before it meets real records (AGENTS.md rule 4:
proof before launch). Real-data numbers still come from data/trial/ with the team pack.
"""
