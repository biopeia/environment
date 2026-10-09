# Environment

This repository contains incremental Biopeia Environment extractions: objective environmental laws, frozen ground-truth descriptions, mutable field/resource state, a finite-resource state model, and the coordinate value used to index that state.

It is not the World authority. World identity, presence, occupancy, movement, event journals, causal ordering/commit, and world checkpoint coordination are deliberately not included. It does not contain study controls, Organism goals, rewards, or learned semantics.

`FiniteResourceState` owns a finite environmental quantity and its local scalar
field. Physics-engine geometry/contact detection and the Lab runtime adapter
remain outside this repository; callers report only the quantity actually
accepted by the receiving body/runtime.

`EnvironmentState.field_values_at(tick)` provides an immutable projection of objective field laws at an explicit non-negative causal tick. It is a pure query: it neither advances Environment state nor reads host time. World remains responsible for selecting and committing causal transitions.

The import package and distribution are both named `environment`. The package uses the Python standard library only. See [`MIGRATION.md`](MIGRATION.md) for exact source provenance, dispositions, and deferred scope.
