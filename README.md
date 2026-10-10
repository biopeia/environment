# Environment

This repository contains bounded Biopeia Environment capabilities: identified finite-resource state, an explicit static physical scene/owner projection, explicit resource geometry projection, and one narrowly scoped deterministic procedural 3D genesis capability. It is not a universal Environment schema, terrain generator, or complete Environment runtime.

Environment owns external environmental truth; World owns shared causal ordering, coordination, commit, and recovery. A numerical solver is not a semantic authority. The static-scene and procedural-genesis capabilities use explicit frame and SI-labelled values and remain independent of any solver implementation. Procedural genesis is one supported option; caller-authored explicit/static scenes remain valid.

Each Environment owner instance is explicitly attached to one `world_id` at
construction. Environment-local `PhysicalStepCorrelation` values are
correlation data derived by an integration adapter from World-issued physical
step context; they are not proof of World authorization. Adoption rejects a
different World binding, mismatched step correlation, non-next causal tick,
or mismatched Environment identity/revision. The World owner identity and
Environment identity remain distinct and are related by World roster
registration, not by identifier equality. Static and dynamic owner
checkpoints persist the World attachment, including before the first adopted
step. These checkpoint schema changes are intentionally strict; earlier
checkpoint versions are not accepted through compatibility decoding.

Checkpointable owners expose `verify_restoration(reference)` to compare an
already restored owner object with an independently supplied committed owner
reference. The reference binds owner identity, schema, and SHA-256 of the
canonical owner checkpoint; owners that persist World or Environment bindings
also require those exact identities/revisions. This verifies owner state only:
it is not a durable store, a World commit decision, or a power-loss guarantee.
The World runtime must pass the committed reference and the restored owner
state to this boundary before resuming; this repository-level API does not by
itself change World's restore orchestration.

`FiniteResourceState` owns a finite environmental quantity and its local scalar field. The resource transfer limit/quantity semantics do not imply physical equivalence to endogenous mechanisms. Physics-engine geometry/contact execution and Lab runtime intervention semantics remain outside this repository.

The former extracted hex-grid fields, cell-based terrain/hydrology, and coupled `EnvironmentState`/field-law APIs were removed because they did not establish a justified TARGET contract. There is no hex-to-3D conversion or backwards-compatibility shim. Procedural sphere placement is target-authored and carries no cognitive labels; it makes no non-overlap or scientific-validity claim. See [`MIGRATION.md`](MIGRATION.md) for scoped provenance, evidence, and limitations; the overall source inventory remains open.

The import package and distribution are both named `environment`. The package uses the Python standard library only.
