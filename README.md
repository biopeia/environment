# Environment

This repository contains the first incremental Biopeia Environment extraction: objective environmental laws, frozen ground-truth descriptions, mutable field/resource state, and the coordinate value used to index that state.

It is not the World authority. World identity, presence, occupancy, movement, event journals, causal ordering/commit, and world checkpoint coordination are deliberately not included. It does not contain study controls, Organism goals, rewards, or learned semantics.

The import package and distribution are both named `environment`. The package uses the Python standard library only. See [`MIGRATION.md`](MIGRATION.md) for exact source provenance, dispositions, and deferred scope.
