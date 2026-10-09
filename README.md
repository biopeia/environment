# Environment

This repository contains bounded Biopeia Environment capabilities: identified finite-resource state, an explicit static physical scene/owner projection, explicit resource geometry projection, and one narrowly scoped deterministic procedural 3D genesis capability. It is not a universal Environment schema, terrain generator, or complete Environment runtime.

Environment owns external environmental truth; World owns shared causal ordering, coordination, commit, and recovery. A numerical solver is not a semantic authority. The static-scene and procedural-genesis capabilities use explicit frame and SI-labelled values and remain independent of any solver implementation. Procedural genesis is one supported option; caller-authored explicit/static scenes remain valid.

`FiniteResourceState` owns a finite environmental quantity and its local scalar field. The resource transfer limit/quantity semantics do not imply physical equivalence to endogenous mechanisms. Physics-engine geometry/contact execution and Lab runtime intervention semantics remain outside this repository.

The former extracted hex-grid fields, cell-based terrain/hydrology, and coupled `EnvironmentState`/field-law APIs were removed because they did not establish a justified TARGET contract. There is no hex-to-3D conversion or backwards-compatibility shim. Procedural sphere placement is target-authored and carries no cognitive labels; it makes no non-overlap or scientific-validity claim. See [`MIGRATION.md`](MIGRATION.md) for scoped provenance, evidence, and limitations; the overall source inventory remains open.

The import package and distribution are both named `environment`. The package uses the Python standard library only.
