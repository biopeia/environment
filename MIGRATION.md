# Environment migration record

## Scope and governing boundary

This record tracks dispositions established by the bounded Environment cleanup; it is not a complete source inventory. Biopeia TARGET separates World causal coordination from Environment-owned external state and dynamics. The canonical embodied path is not constrained to the historical hex topology. The migration rule is explicit: legacy or unwanted code is not retained, wrapped, mechanically converted, or given compatibility shims merely to preserve old behavior.

## Source provenance

- Source repository: historical `symbiont-lab` monorepo, source root `environment/`.
- Pinned source tree recorded by the original extraction: `80d372a186513035f85a769db886e505cabba52d`.
- Relevant extraction provenance: `13720935595fedabec2c376dc933629b0deae5aa` (domain restructuring); `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab` (environment/genesis extraction and adapter relocation); `b61eefbe3a09d2da29dc8eb3f69c2fb9f4ed5f5f` (read-only tick accessor).
- These references identify ancestry only; no synthetic source history is claimed. The source repository was not modified for this change.

## Scoped dispositions

| Source symbol/path | Former Biopeia target path | Disposition now | Evidence and reason |
| --- | --- | --- | --- |
| `environment/src/environment/topology.py::HexCoord` | `src/environment/spatial.py` | DROP | Source: `environment/src/environment/topology.py`, extracted by source commit `13720935595fedabec2c376dc933629b0deae5aa`. Axial `q/r` coordinates, six-neighbor navigation, and hex distance encoded the historical discrete topology. Its only references in this workspace were the Environment package and its tests; two integration fixtures were retargeted to explicit fixture input instead of a hex field. No conversion to 3D and no compatibility shim. |
| `environment/src/environment/terrain.py::DynamicGeography` static fields / `TerrainFieldState` | `src/environment/terrain.py` | DROP | Source: `environment/src/environment/terrain.py`, pinned blob `7b241ec9e6cd1f854a0052428800bcd9b83dd7b2`, path extraction source commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`. The extracted state was a finite rectangular `HexCoord` map with copied source formulas and seed phase, not a justified general Environment contract. Workspace consumers were limited to its tests; no production runtime consumer was found. |
| `DynamicGeography._initialize_surface_water` | `src/environment/surface_water.py` | DROP | Source: `DynamicGeography._initialize_surface_water` in the same pinned `terrain.py` blob/path commit above. Cell-keyed initialization and thresholds inherit the hex grid and copied terrain formulas; package/workspace use was limited to tests. No grid-to-3D adapter or replacement model is claimed. |
| `DynamicGeography.step()` surface-water update | `src/environment/hydrology.py` | DROP | Source: `DynamicGeography.step()` in the same pinned `terrain.py` blob/path commit above. Update depended on the same cell adjacency, terrain fields, and source-specific coefficients. It was exercised only by its focused package test. No validated physical hydrology model is implied. |
| `WorldEnvironment` / target `EnvironmentState`, `GroundTruth`, regional resource/hazard lookup | `src/environment/genesis.py` | DROP | Source: `environment/src/environment/genesis.py`, extracted at source commit `43a65f0ab220adbcd7afce6fccb3f07e91eb77ab`; field projection evolved at `b61eefbe3a09d2da29dc8eb3f69c2fb9f4ed5f5f`. This API mixed field laws with `HexCoord`-keyed resource pools, cell/region lookup, and an Environment checkpoint whose payload retained those semantics. Workspace-wide consumers were the two integration fixtures listed below and legacy-focused Environment tests. There is no substitute universal Environment schema in this change. |
| `PeriodicFieldLaw`, `ResourceLaw`, `HazardLaw` | `src/environment/laws.py` | DROP | Source: `environment/src/environment/laws.py` at pinned source SHA above. These copied scalar laws had no production consumers beyond the removed genesis path; their tests asserted implementation behavior, not ratified units, physical meaning, or scientific validation. |
| `effective_permeability`, `effective_fertility`, `resource_renewal_factor` | `src/environment/ecology.py` | DROP | Source: `environment/src/environment/terrain.py` pinned blob above, methods `effective_permeability`, `effective_fertility`, and `resource_renewal_factor`. Pure formulas were extracted from `DynamicGeography` but have no independent target contract or production consumer; only their focused tests referenced them. |
| `FiniteResourceState` | `src/environment/resource.py` | RETAIN | Independent Environment-owned finite quantity state; production consumer is Lab's `src/lab/interventions/material_transfer.py`, with integration coverage in `lab/tests/integration/test_material_transfer_intervention.py`. This claim is limited to controlled scalar transfer/state, not physical equivalence to an endogenous mechanism. Original source behavior was derived from `environment/src/environment/physics3d/resource.py` at pinned source SHA above; mechanism commits `7f526ddc1d2393e8b7af41a967dfd6af8cc6aa87`, `7dd33065829f2afc17281797bcdcb143d015e6f5`, and `a2b98b78604866b7c539dae75a48e64a74d547f4`. |
| `IdentifiedFiniteResource` | `src/environment/identified_resource.py` | RETAIN | Typed identity/checkpoint wrapper around finite resource state, consumed by the same Lab material-transfer implementation and integration test. No Environment geometry or hex dependence. |
| `StaticPhysicalScene`, `StaticEnvironmentOwner` | `src/environment/static_scene.py` | RETAIN | Target-authored explicit frame/SI scene and owner adoption/checkpoint boundary; used by `tests/integration/test_first_biopeia_physical_causal_step.py` and Environment's `tests/test_static_scene.py`. This is a narrow static fixture capability, not a universal Environment schema or procedural terrain model. |
| Explicit resource geometry projection | `src/environment/physical.py` | RETAIN | Target-authored, explicit-frame and caller-scale projection from resource-relative lengths. This is not copied hex behavior and makes units/frame explicit; it remains separate from solver execution and semantic authority. It currently has test coverage but no production consumer; that caveat does not justify retaining legacy behavior or imply completed physical integration. No old API alias is provided. |

## Workspace integration consumers

The following consumers of the removed field-law APIs were updated locally in the unversioned workspace integration suite (the workspace root is not a Git repository; these edits are intentionally not part of this Environment PR):

- `tests/integration/test_first_biopeia_causal_tick.py`: removed `EnvironmentState`/`PeriodicFieldLaw`; the deterministic transduction/cognition path now receives an explicit fixture signal. The test still exercises the same bounded Organism command, Embodiment candidate, World publication, and passive Observation path; it does not claim Environment field semantics.
- `tests/integration/test_durable_checkpoint_restore_slice.py`: removed the obsolete Environment field/checkpoint participant; retained the multi-owner Organism/Embodiment World manifest publication, restart, and continuation purpose. Environment participation in physical causal commit is covered separately by `test_first_biopeia_physical_causal_step.py`.

Workspace-wide reference searches found no remaining consumers of the removed Environment APIs outside their removed tests and the two retargeted fixtures. The retained resource and static-scene capabilities have the consumers identified above. This is a scoped consumer check, not proof that the complete historical Environment inventory has been classified.

## Compatibility and completion limits

No compatibility layer is provided for `HexCoord`, `TerrainFieldState`, `EnvironmentState`, `GroundTruth`, field laws, ecology helpers, or surface-water APIs. No hex-to-3D conversion is provided. Callers must use a separately justified TARGET capability or own an explicit experimental fixture; removed APIs are not silently emulated.

This disposition covers only the symbols and consumers listed here. The broader MOVE/SPLIT/REWRITE/DROP/DEFER source inventory remains open, and `DEFER` items are not final dispositions. Passing tests do not establish ecological/hydrological scientific adequacy, physical calibration, or completion of Environment migration.
