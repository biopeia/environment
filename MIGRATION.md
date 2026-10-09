# Environment migration record

## Source and provenance

- Source repository: local Biopeia source monorepo `symbiont-lab` (`/home/alessbarb/workspace/repos/active/symbiont-lab`)
- Source SHA: `80d372a186513035f85a769db886e505cabba52d`
- Architecture audit baseline: `cef998a55aae32ed8b2f7373079c11667b01e915`
- Source root: `environment/`
- Relevant source commits: `13720935595fedabec2c376dc933629b0deae5aa` (five-domain restructuring), `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab` (environment/genesis extraction and world-adapter relocation), `b61eefbe3a09d2da29dc8eb3f69c2fb9f4ed5f5f` (Environment read-only tick accessor). These source commits are provenance only; no synthetic source history is claimed in this repository.
- Migration is copy-first. The source tree remains untouched.

## Included pieces

| Target path | Source path | Disposition | Notes |
| --- | --- | --- | --- |
| `src/environment/laws.py` | `environment/src/environment/laws.py` | MOVE | Environmental field, resource, and hazard laws; copied from the pinned source. |
| `src/environment/genesis.py` | `environment/src/environment/genesis.py` | SPLIT | Retains `GroundTruth` and environmental field/resource runtime state. `WorldEnvironment` was renamed `EnvironmentState`; import of coordinate type now points to the extracted value object. |
| `src/environment/spatial.py` | `environment/src/environment/topology.py` (`HexCoord` only) | SPLIT | Contains only the coordinate value object needed to index spatial environment state. Placement, occupancy, grid bounds, and move resolution are not copied. |
| `src/environment/resource.py` | `environment/src/environment/physics3d/resource.py` (finite source state only) | SPLIT | Extracts the environment-owned position/radii, scalar field, finite quantity, bounded offer/accepted-consumption, and v1 checkpoint payload as `FiniteResourceState`. PhysicsScene geometry/contact detection and runtime/Organism wiring are excluded. |
| `src/environment/physical.py` | `environment/src/environment/physics3d/resource.py::PhysicalResource` geometry | REWRITE | Requires an explicit `FrameDescriptor` and caller-declared `meters_per_resource_unit`; emits center/radius in metres without transforming out of that frame. This is configured scaling, not calibration evidence. No old API compatibility is retained. |
| `src/environment/__init__.py` | Source package exports | REWRITE | Explicit minimal Environment-only public surface; no exports for World or Observation responsibilities. |
| `tests/unit/test_laws.py` | `environment/tests/unit/world/test_laws.py` | MOVE | Focused law tests. |
| `tests/unit/test_genesis.py` | `environment/tests/unit/world/test_genesis.py` | SPLIT | Focused environmental-state coverage; import updated to `EnvironmentState` and `HexCoord`. |
| `tests/unit/test_genesis_regional.py` | `environment/tests/unit/world/test_genesis_regional.py` | SPLIT | Focused regional environmental-law coverage; imports updated. |
| `src/environment/ecology.py` | `environment/src/environment/terrain.py` (`DynamicGeography.effective_permeability`, `effective_fertility`, `resource_renewal_factor`) | SPLIT | Pure equations for existing ecological fields; no cell storage, topology, units, persistence, or World traversal behavior. |

## Deferred or excluded source families

| Source path/family | Disposition | Reason |
| --- | --- | --- |
| `environment/src/environment/checkpoint.py`, `state.py`, `events.py`, `deferred.py` | DEFER | World checkpoint, transaction, journal, and causal event coordination responsibilities. |
| `environment/src/environment/constitution.py` | DEFER | `WorldConstitution` fingerprints topology, interaction/resolution, lifecycle, and RNG contracts; belongs to World coordination pending its extraction. |
| `environment/src/environment/contracts.py`, `observation.py` | DEFER | World action/presence contracts and passive projections belong to World/Observation boundary work, not objective environment state. |
| `environment/src/environment/movement.py` | DEFER | Resolves organism movement and shared occupancy, a World/Embodiment interaction. |
| `environment/src/environment/topology.py` remainder (`BodyPlacement`, `HexTopology`, `OccupancyGrid`) | DEFER | Body placement and occupancy are World presence/coordination. The target takes only `HexCoord` as a spatial key. |
| `environment/src/environment/terrain.py` | DEFER | Mixed source: environmental terrain/ecology is combined with topology-dependent traversal, occupants, density, and World-facing cell projection. Requires a deliberate split rather than whole-file copy. |
| `environment/src/environment/genesis_v1.py`, `genesis_v2.py` | DEFER | Scenario builders couple objective environmental laws to World constitution and Observation signal identifiers. |
| `environment/src/environment/rng.py` | DEFER | Current API is explicitly World-namespaced RNG. Environment-specific random-stream ownership must be established at the World contract boundary before extraction. |
| `environment/src/environment/physics3d/environments.py` | DEFER | Contains lab-specific nursery/study stimuli and metabolic support in addition to physical fixtures; copying it would import experimental intervention semantics. |
| `environment/src/environment/physics3d/resource.py` (scene adapter portions) | DEFER | PhysicsScene geometry and contact execution are substrate/World-boundary concerns; these portions were intentionally not copied into the Environment state model. |
| source `environment/tests` not listed above | DEFER | Tests cover excluded World, Observation, mixed terrain, scenario-builder, or integration responsibilities. |

## Known rewrites

1. `WorldEnvironment` is named `EnvironmentState` in the target to avoid implying ownership of World identity/causal coordination.
2. `HexCoord` was split from the mixed World topology module into `environment.spatial`; `BodyPlacement`, `HexTopology`, and `OccupancyGrid` remain deferred.
3. The package export surface is intentionally narrower than the source package.
4. Python import namespace and distribution are both named `environment`.
5. Added `EnvironmentState.field_values_at(tick)` as a target-facing, immutable
   environmental field projection for an explicit non-negative causal tick.
   This is `REWRITE`/new boundary functionality, not a claim that the source
   monolith already exposed a pure projection API. It evaluates the existing
   `GroundTruth` laws without changing Environment state or consulting host
   time, allowing World to request values for a proposed causal transition.
6. Added deterministic `EnvironmentState.checkpoint_bytes()` and
   `from_checkpoint_bytes(...)` for Environment-owned mutable state. The payload
   records the causal tick, field projection, and resource pools; it does not
   serialize `GroundTruth`. Restore uses caller-supplied configuration and
   checks the stored field projection against its laws, but does not verify full
   configuration identity (including resource, hazard, or regional laws). The
   immutable configuration identity/reference and cross-authority publication
   remain the responsibility of World integration; this API alone is not a
   durable World checkpoint or a crash-recovery guarantee.
7. Split the finite physical resource in the pinned source into `FiniteResourceState`.
   Exact scalar field, offer/accepted-consumption, and checkpoint behavior were
   derived from `environment/src/environment/physics3d/resource.py` at source
   SHA `80d372a186513035f85a769db886e505cabba52d`. The mechanism originated in
   source commit `7f526ddc1d2393e8b7af41a967dfd6af8cc6aa87`; depletion behavior
   was added in `7dd33065829f2afc17281797bcdcb143d015e6f5`, and debit was bounded
   by accepted intake in `a2b98b78604866b7c539dae75a48e64a74d547f4`. Scene
   integration was retargeted in `0f75c709bba8bfc9505a769662e9bf0e8e7e074a`.
   The extracted state model validates finite 3D geometry and positive/bounded
   configuration; it does not perform contact detection, construct colliders,
   determine intake, or wire Organism/Embodiment transitions. It preserves the
   source v1 resource checkpoint shape. This is not proof that the prior runtime
   integration conforms to the TARGET authority contract.

8. Split the deterministic static terrain-field initialization from the mixed
   source `DynamicGeography` into `TerrainFieldState`. Provenance: pinned source
   `environment/src/environment/terrain.py` at source SHA
   `80d372a186513035f85a769db886e505cabba52d`, introduced into that path by
   source commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`; source behavioral
   test reference is
   `lab/tests/unit/lab/world/test_terrain_and_movement.py`. Disposition:
   `SPLIT`. The extraction contains only deterministic initialization and
   read-only access for elevation, permeability, moisture, temperature, and
   fertility. It does not copy traversal, topology bounds, occupancy, hydrology,
   disturbance, detritus, ecological pressure, organism-presence/death inputs,
   substrate impulse, or checkpoint serialization. The generation seed and
   dimensions are explicit inputs; source modulo-1000 seed phase and numeric
   formulas/rounding are preserved. The source tests live with Lab's World
   tests and do not by themselves establish that this mechanism is active in
   productive runtime or scientifically validated. This target module is an
   owner-aligned environmental state candidate, not evidence that the old
   DynamicGeography path should be retained wholesale.

9. Rewrote `PhysicalSphere` and `project_resource_geometry(...)` as an explicit
   Environment-owned geometry projection boundary, derived from
   `environment/src/environment/physics3d/resource.py::PhysicalResource` at
   source SHA `80d372a186513035f85a769db886e505cabba52d`. The source exposes no
   physical unit or frame on `PhysicalResource`, so callers must now provide a
   valid `FrameDescriptor` and positive finite `meters_per_resource_unit`.
   The projection emits `center_m` and `radius_m`, records the scale used, and
   leaves coordinates local to the declared frame; it does not transform them
   into the parent frame. Source positions, physical radius, and scalar
   `field_radius` share relative length units, but only position and physical
   radius are projected (`field_radius` is not a collider). The supplied scale
   is explicit runtime configuration, not calibration, scientific evidence,
   or a claim of physical equivalence; material quantity and transfer-limit
   units remain unresolved. No compatibility API preserves the old unitless
   projection. `environment/physics3d/environments.py` documents metres and
   Z-up for its versioned recipes, but that does not establish those semantics
   for every resource instance. Contact material, solver construction,
   coupling, and accepted state transitions remain outside Environment. This
   remains a partial physical projection only, not completion of Objective
   §14.

10. Split three pure field equations from `DynamicGeography` into
   `src/environment/ecology.py`. Provenance: pinned source
   `environment/src/environment/terrain.py` at source SHA
   `80d372a186513035f85a769db886e505cabba52d`, blob
   `7b241ec9e6cd1f854a0052428800bcd9b83dd7b2` (methods
   `effective_permeability`, `effective_fertility`, and
   `resource_renewal_factor`). Disposition: `SPLIT`. Coefficients, clamp
   bounds, and the renewal floor are retained literally. This extracts only
   calculations over caller-supplied scalar fields; it does not transfer
   `DynamicGeography` state, establish physical units or scientific validity,
   define input validation beyond the source behavior, or include adjacent
   topology-dependent traversal and dynamic update rules.

11. Split deterministic initial surface-water values from the mixed source
   `DynamicGeography._initialize_surface_water`. Provenance: pinned source
   `environment/src/environment/terrain.py` at source SHA
   `80d372a186513035f85a769db886e505cabba52d`, introduced into that path by
   source commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`. Disposition:
   `SPLIT`. `initialize_surface_water` requires explicit, complete moisture,
   elevation, and permeability mappings for every cell in the provided finite
   rectangular dimensions. It preserves the source formula, cutoff, clamp,
   and four-decimal rounding. It deliberately does not inherit the source
   constructor's empty-map generation or partial-map override behavior, and it
   does not provide implicit field defaults. The function is initialization
   only: `DynamicGeography.step`, substrate impulses, occupant inputs,
   persistence, World transaction state, and runtime/Lab wiring remain
   excluded. Existing source coverage is
   `lab/tests/unit/lab/world/test_terrain_and_movement.py::test_surface_water_is_deterministic_and_persistent_roundtrip`; it asserts
   repeatability and serialization roundtrip, not a numeric formula oracle.
   New target tests exercise the numeric formula, threshold, clamp, immutable
   result, and complete-input requirement. This does not validate a scientific
   hydrology model or claim that CURRENT runtime callers use this extracted
   function.

## Validation scope

The selected package has no first-party runtime dependency beyond the Python standard library. Validation is scoped to the copied/split laws and environmental-state unit tests. Passing tests do not establish scientific adequacy of any ecological law or complete migration of the source Environment package.

## Additional slice: dynamic surface-water relaxation

| Source element | Disposition | Target path | Provenance / boundary |
| --- | --- | --- | --- |
| `DynamicGeography.step()` surface-water transition, source lines 366–390 (equilibrium, relaxation, temperature loss, downhill-neighbor inflow, sparse threshold, rounding) and getter defaults at lines 190–200 | SPLIT / REWRITE | `src/environment/hydrology.py::advance_surface_water` | Source repository SHA `80d372a186513035f85a769db886e505cabba52d`; `environment/src/environment/terrain.py`, blob `7b241ec9e6cd1f854a0052428800bcd9b83dd7b2`, path commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`. Source active-set construction at lines 358–365 and occupancy/death interpretation are deliberately not copied. |
| Focused deterministic transition tests | REWRITE | `tests/test_hydrology.py` | `test_relaxes_water_toward_equilibrium_and_keeps_source_rounding`, `test_expands_active_set_by_one_neighbor_and_applies_downhill_inflow`, sparse-threshold, explicit-grid-bound, finite-input, and non-mutation assertions. |

The extracted transition is a pure update over caller-supplied Environment-owned
water/static-field maps and an explicit valid-cell set. The caller supplies the
candidate cells that correspond to the source union of presence/death and
active ecological state; this module does not interpret occupancy, death,
World topology, or lifecycle. It preserves source defaults for missing static
fields (`0.5` moisture/elevation/temperature and `0.8` permeability),
coefficients, threshold (`0.002`), and four-decimal rounding. Unlike the mixed
source method, it rejects input state/candidates outside the supplied grid and
rejects non-finite field values. It does not implement substrate impulse,
other ecological decays, checkpointing, or scientific calibration. This is
non-overlapping with the surface-water initialization-only candidate (#7),
the pure effective-field equations (#9), and physical geometry projection
(#8). The source monorepo remains unchanged.

## Additional slice: sparse ecological-field decay equations

| Source element | Disposition | Target path | Provenance / boundary |
| --- | --- | --- | --- |
| `DynamicGeography.step()` sparse trace, disturbance, detritus, and ecological-pressure decays, source lines 392–420 | SPLIT | `src/environment/ecology.py::decay_traces`, `decay_disturbance`, `decay_detritus`, `decay_ecological_pressure` | Source repository SHA `80d372a186513035f85a769db886e505cabba52d`; `environment/src/environment/terrain.py`, blob `7b241ec9e6cd1f854a0052428800bcd9b83dd7b2`, path commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`. |
| Source qualitative trace and pressure tests | REWRITE | `tests/unit/test_ecology.py::test_sparse_decay_preserves_threshold_rounding_and_input` | Source test file `lab/tests/unit/lab/world/test_terrain_and_movement.py`, blob `7f72c92bdd27522de8de0e8b0f322daf0a5a646a`; source tests `test_traces_deposit_and_decay` and `test_dynamic_ecology_presence_creates_pressure_and_then_decays` assert qualitative behavior rather than exact sparse cutoffs. |

The four functions retain the source multipliers (`0.94`, `0.88`, `0.985`,
`0.92`), sparse retention thresholds (`0.005`, `0.005`, `0.002`, `0.002`),
threshold-before-rounding order, and four-decimal rounding. Each returns a new
mapping and does not mutate its input. This extracts only pure value-map
equations. Tick ordering, occupancy/death interpretation and deposition,
active-cell selection, topology traversal, World state, and persistence remain
caller-owned and are not migrated. These are preserved current software rules,
not claims of scientific validity or calibration.

## Rejected source slice: hex-bound substrate impulse

| Source path/symbol | Source commit / pinned revision | Target disposition | Reason, evidence, and caveats |
| --- | --- | --- | --- |
| `environment/src/environment/terrain.py::DynamicGeography.apply_directional_impulse` | Path commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`; source SHA `80d372a186513035f85a769db886e505cabba52d`; blob `7b241ec9e6cd1f854a0052428800bcd9b83dd7b2` | `DROP` from target repository `biopeia/environment`; no target path | The implementation and tests depend on `HexCoord` and finite q/r grid bounds, and its normalized/clamped `magnitude` has no physical unit or reference frame. The behavior is not an engine-independent physical contract and has no ratified scientific/physical semantics for the canonical continuous-3D path. Source behavior/tests remain in the intact historical monorepo as evidence only. No hex compatibility API is provided. Source test references: `lab/tests/unit/lab/world/test_terrain_and_movement.py::test_directional_impulse_redistributes_existing_substrate_without_semantic_action` and `test_substrate_impulse_is_transactionally_rolled_back`; `lab/tests/unit/lab/world/test_actuation_adapter.py` also calls the method. The candidate Biopeia/environment PR #15 was closed without merge. |

## New target capability: explicit static 3D scene fixture

`src/environment/static_scene.py` introduces a small Environment-owned target
capability, classified `REWRITE` / new target capability rather than a migration
of legacy code. It projects explicit static ground-plane geometry, frame identity,
SI gravity and stable object identities; its owner validates unchanged-scene
adoption against Environment identity/revision and strictly sequential causal
ticks, and provides deterministic owner-bound checkpoint bytes. This is not a
solver contract, general scene schema, World runtime, HexCoord conversion, or
backward-compatibility layer. No legacy source symbol is claimed as its source.

## Existing discrete spatial implementation: provisional disposition only

The target package still contains the historical discrete spatial family; it
is not the canonical embodied Environment path and is not used by the new
static 3D projection. Current code inspection found `HexCoord` imported by
`genesis.py`, `terrain.py`, `hydrology.py`, and `surface_water.py`; these types
are exercised by Environment unit tests. `src/environment/__init__.py` currently
exports both `HexCoord` and `TerrainFieldState`. `TerrainFieldState` is defined
in `terrain.py` and its tests still consume it through the package export.
The earlier `SPLIT`/`DEFER` rows above record what was copied and what was
excluded at those migration steps; they are not approval to retain the copied
legacy implementation as TARGET. The remaining discrete family has only a
provisional inventory status until every material source symbol and active
consumer is classified against the ratified World/Environment split. No new
hex/discrete source code may be copied, extended, or exposed to preserve an old
API or behavior while that audit is open. Existing package/test consumers do
not by themselves justify a TARGET role.

For each symbol, the audit must decide whether a capability has independently
justified TARGET meaning and should be newly implemented on its own terms, or
whether the old implementation is `DROP`, `REWRITE`, or a temporary `DEFER`
with no compatibility promise. A discrete scientific fixture remains an
allowed future capability, but does not authorize carrying forward this legacy
implementation. No mechanical HexCoord-to-3D conversion, compatibility
adapter, or canonical embodied use is authorized. Preserve source evidence in
the original repository where scientifically or provenance-relevant; do not
delete that source as part of this target disposition work.

## Per-symbol disposition: historical hex-spatial family

This inventory corrects the earlier extraction record; it does not erase the
fact that these slices were copied into the target repository. `REWRITE` means
that an independently justified TARGET capability may be newly implemented.
It does not authorize retaining historical code, formulas, data formats, APIs,
or behavior for backward compatibility. Preserve historical source and tests
in the original repository as provenance, not as a target compatibility suite.

| Source path / symbol | Source provenance | Existing target extraction | Disposition and target meaning |
| --- | --- | --- | --- |
| `src/symbiont_world/topology.py::HexCoord` (at the pinned source revision, moved to `environment/src/environment/topology.py`) | Source SHA `80d372a186513035f85a769db886e505cabba52d`; introduced by `7d043253e9e855674fbe363cd17184bd42be8ef4`, moved into Environment at `13720935595fedabec2c376dc933629b0deae5aa`; blob `2bdd5eb8e99b48fb70611c78cc46cdc51a3a2415`. | `src/environment/spatial.py`, target commit `7c0efdb7264596aff5a43b0fe2041dd81aa53c02`; blob `8b5d87c8b68a0453f3c3552c0f21626e4139ca53` at target `main` head `45fd868957e69c6cfd66a685c7ad6ce74ed8ab76`. | `DROP` legacy code and API. It is q/r integer coordinates with six-neighbor and hex-distance semantics, not the canonical embodied 3D contract. A future discrete experimental index would require independent justification and a new implementation; no mechanical conversion or compatibility API. |
| `TerrainFieldState` (derived from `DynamicGeography` field initialization/accessors; no source class with this name) | `environment/src/environment/terrain.py`; source SHA `80d372a186513035f85a769db886e505cabba52d`; path commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`; blob `7b241ec9e6cd1f854a0052428800bcd9b83dd7b2`. | `src/environment/terrain.py`, target commit `b22c88f9f44b6ba41b451529beac1be259fc2770`; target blob `f50b1eed8028535e621bf357fec49cf8be9136aa`. | `REWRITE` only the broad Environment-owned field/condition capability if justified; `DROP` the copied class, finite q/r dimensions, seed phase/formulas, and untyped scalar API. Existing tests prove deterministic implementation properties, not scientific or physical validity. Any new capability must define its spatial meaning and units. |
| `initialize_surface_water` (source `DynamicGeography._initialize_surface_water`) | `environment/src/environment/terrain.py`; source SHA `80d372a186513035f85a769db886e505cabba52d`; introduced by `4070a81173a90c5f01dbf9db046b3c1ceb7fe9c0`, moved by `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`; blob `7b241ec9e6cd1f854a0052428800bcd9b83dd7b2`. | `src/environment/surface_water.py`, target commit `9b3affaddee18e683b54bf5f5be796aba145ee8c`; blob `14b33334a997152d20b7a072130474a4125da7cb`. | `DROP` this implementation and capability. It uses finite HexCoord maps and uncalibrated scalar fields/cutoff/clamp/rounding without physical water units or an independently affirmed need. Any later water initialization needs separately justified Environment state/semantics and a new implementation. |
| `advance_surface_water` (source `DynamicGeography.step()` surface-water transition) | `environment/src/environment/terrain.py`; source SHA `80d372a186513035f85a769db886e505cabba52d`; path commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`; blob `7b241ec9e6cd1f854a0052428800bcd9b83dd7b2`. | `src/environment/hydrology.py`, target commit `fb44cf4c0cff793ca1c64a3a54d5d74a6a3991d0`; blob `3c8d4d025ee3877275d28270177feb8f279f4a34`. | `DROP` this transition. Legacy coefficients/defaults, neighborhood flow, sparse cutoffs and rounding do not establish hydrological validity, units, physical timestep, conservation, or solver/World adoption. A future hydrology capability needs separate semantic/physical and scientific justification and a new implementation. |
| `GroundTruth` | `src/symbiont_world/genesis.py` (at the pinned revision, moved to `environment/src/environment/genesis.py`); source SHA `80d372a186513035f85a769db886e505cabba52d`; initial source `7d043253e9e855674fbe363cd17184bd42be8ef4`, regional additions `0dc2df5f480da245b37c10b41eed11e832c7fbee` and `b9dda68d8329339eb402b9349d54ebcc92dd3268`, moved by `13720935595fedabec2c376dc933629b0deae5aa`; tick exposure at `b61eefbe3a09d2da29dc8eb3f69c2fb9f4ed5f5f`; blob `34d90b1b33c1434d6b21164c9ceced08603d2271`. | `src/environment/genesis.py`, target extraction commit `7c0efdb7264596aff5a43b0fe2041dd81aa53c02`; blob `1f9876b635b861fc097a787fa5fddab357d01846` at target `main` head `45fd868957e69c6cfd66a685c7ad6ce74ed8ab76`. | `REWRITE` representation and contract. Preserve only independently justified Environment ownership of external laws/genesis. Do not preserve `region_of(HexCoord)`, regional resource/hazard table shapes, numeric conventions, or require a global `GroundTruth` label/API. |
| `EnvironmentState` | Same source path, pinned SHA and blob as `GroundTruth`; legacy mutable state originated with `7d043253e9e855674fbe363cd17184bd42be8ef4`, moved by `13720935595fedabec2c376dc933629b0deae5aa`, with later revision `b61eefbe3a09d2da29dc8eb3f69c2fb9f4ed5f5f`. | `src/environment/genesis.py`, checkpoint implementation target commit `eb55c1c703cbf770216733da51a7604279338cba`; blob `1f9876b635b861fc097a787fa5fddab357d01846` at target `main` head `45fd868957e69c6cfd66a685c7ad6ce74ed8ab76`. | `REWRITE` implementation, API and checkpoint format. Environment owns its state and supplies owner checkpoint references; the World commit contract requires those references to be durably identifiable and recoverable before commit. HexCoord-keyed pools and v1 checkpoint bytes are not retained. Preserve owner adoption/recovery semantics as contract, not old serialization compatibility. Workspace consumers are `tests/integration/test_first_biopeia_causal_tick.py` and `test_durable_checkpoint_restore_slice.py`; retarget their assertions to replacement semantics. |

## Removal sequence and current gap

The target package tests/dependencies to account for are
`tests/unit/test_terrain.py`, `tests/unit/test_surface_water.py`,
`tests/test_hydrology.py`, `tests/unit/test_genesis.py`,
`tests/unit/test_genesis_regional.py`, and
`tests/test_environment_checkpoint.py`, plus exports in
`src/environment/__init__.py`. Workspace fixtures consume genesis/state in
`tests/integration/test_first_biopeia_causal_tick.py` and
`test_durable_checkpoint_restore_slice.py`. These consumers do not authorize
keeping the legacy APIs.

Historical behavior tests in the source monorepo include
`lab/tests/unit/lab/world/test_terrain_and_movement.py`; they document source
behavior but do not validate physical or scientific adequacy of the copied
formulae.

The sequence is to implement the justified Environment-owned genesis/state
and checkpoint contract against current World owner-recovery contracts,
retarget the workspace causal/recovery fixtures, then remove the dropped
HexCoord, field-generation and water/hydrology implementations, exports and
legacy-specific target tests. Until that sequence is complete, the current
hex-bound target code is an explicit migration gap, not an approved final
state. Tests retained after replacement must exercise the new contract, not
act as historical compatibility tests.
