# Module 10 — the second source

`second_source.py` joins FDA approval records to ClinicalTrials.gov trial
records on the same six therapy classes.

## What it shows

**Answering a question one source cannot settle.** The trial registry says
what is *starting*. It cannot say what is *arriving* — which crowded therapy
classes actually convert development activity into approved products, and
which are still purely developmental. Approvals data answers that, but only
once both sides are put on the same class vocabulary.

**Joining on a shared vocabulary rather than on names.** Both sides are
mapped onto the same six classes before the join, so the comparison is
between like and like. Matching on drug or sponsor names would have looked
easier and been wrong.

**A derived rate, not a raw count.** The output is approvals per 1,000
trials, plus a first-approval year per class. A raw approval count would have
ranked the biggest classes first and said nothing about conversion.

## What is not here

The classifier that assigns therapy classes, its three-labeler validation,
the fetch and cleaning stages, and the dashboard. This is the analysis layer
that consumes them.

This project was self-directed rather than a prescribed exercise — the
question, the sources and the method were mine — which is why a fuller slice
of it appears here than for the other modules.

The [dashboard](https://carolinekim.dev/demos/trials) it feeds is public, and
the [case study](https://carolinekim.dev/projects/10) covers the classifier
validation and the audited miss rate.
