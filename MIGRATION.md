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
| `src/environment/__init__.py` | Source package exports | REWRITE | Explicit minimal Environment-only public surface; no exports for World or Observation responsibilities. |
| `tests/unit/test_laws.py` | `environment/tests/unit/world/test_laws.py` | MOVE | Focused law tests. |
| `tests/unit/test_genesis.py` | `environment/tests/unit/world/test_genesis.py` | SPLIT | Focused environmental-state coverage; import updated to `EnvironmentState` and `HexCoord`. |
| `tests/unit/test_genesis_regional.py` | `environment/tests/unit/world/test_genesis_regional.py` | SPLIT | Focused regional environmental-law coverage; imports updated. |

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
| `environment/src/environment/physics3d/resource.py` | DEFER | Physical engine scene ownership and contact execution are substrate/World-boundary concerns; no engine dependency is introduced into this first Environment slice. |
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

## Validation scope

The selected package has no first-party runtime dependency beyond the Python standard library. Validation is scoped to the copied/split laws and environmental-state unit tests. Passing tests do not establish scientific adequacy of any ecological law or complete migration of the source Environment package.
