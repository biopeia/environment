# Environment Static Render Scene v1 — proposed contract

**Status:** PROPOSED — design candidate for Environment Owner review; not an approved contract.
**Issue:** [biopeia/environment#73](https://github.com/biopeia/environment/issues/73)
**Reviewed source:** Environment `d09e45c40633c9b2bf927c7aec3f6326318c2ea8` (`origin/main`); World `51cea9f8975fbdea603592fa5e9c56b073a2f4d4` (`origin/main`, M1 source configuration); Observation `a8b43af65b79ca4e2455bfc1ff1b55faf3d4d353` (`origin/main`, local bridge default cap).
**Scope:** Environment-owned, read-only static render descriptor for passive local visualization.

This proposal turns the accepted design base into a reviewable bounded shape. It does not authorize code, API/transport, publication, remote exposure, or a new observation family. It makes no claim that Environment frames are compatible with Embodiment or World frames, and it does not authorize a composed scene.

## 1. Owner boundary and source support

Environment owns the truth represented by its scene, frame, ground-plane and sphere values. The proposed projection carries only those already modeled display values. It does not expose solver or genesis configuration and does not derive geometry from scalar fields.

Current source types are `FrameDescriptor`, `StaticGroundPlane`, `StaticSphere`, and `StaticPhysicalScene` in `src/environment/static_scene.py`. Existing validation enforces a right-handed orthonormal frame basis, a unit ground-plane normal, positive sphere radius, unique object IDs, and a sphere frame equal to the scene frame. Existing `EnvironmentPhysicalProjection.geometry_revision` is not suitable as a render digest: `_geometry_revision` includes gravity and sliding-friction values as well as geometry.

The current M1 profile supplies `objects=()` and does not invoke procedural genesis. Its Environment geometry is therefore empty. This proposal does not change that configuration and does not authorize synthesizing a floor, sphere, or other object.

## 2. Proposed closed descriptor

```json
{
  "schema_version": 1,
  "environment_id": "environment.demo",
  "environment_revision": "r1",
    "render_geometry_sha256": "022f7875e378b8d9196f13528af47723ffd352f70e379e404946acb3ddc41a9d",
  "length_unit": "m",
  "frame": {
    "frame_id": "environment.frame",
    "parent_frame_id": "environment.parent-frame",
    "origin_m": [0, 0, 0],
    "x_axis_in_parent": [1, 0, 0],
    "y_axis_in_parent": [0, 1, 0],
    "z_axis_in_parent": [0, 0, 1],
    "handedness": "RIGHT_HANDED",
    "up_axis": "Z"
  },
  "items": []
}
```

The envelope and `frame` are required even when `items` is empty. `items: []` means exactly “this projection contains no Environment render geometry.” A consumer must show an explicit empty/unavailable Environment layer; it must not add a default floor or infer geometry. The frame descriptor alone does not assert any relationship to another domain's frame.

The proposed `items` field is a closed union containing only:

```json
{
  "object_id": "ground-z",
  "kind": "ground_plane",
  "frame_id": "environment.frame",
  "normal": [0, 0, 1],
  "offset_m": 0
}
```

or

```json
{
  "object_id": "sphere-a",
  "kind": "sphere",
  "frame_id": "environment.frame",
  "center_m": [1, 0, 0],
  "radius_m": 0.25
}
```

`ground_plane` represents the infinite plane `normal · position_m = offset_m` in the named scene frame, matching `StaticGroundPlane` semantics. No finite boundary or thickness is implied. Any finite camera-dependent drawing crop is a presentation-only viewport choice and must not be presented as Environment-authored extent. `sphere` coordinates and radius are in metres in the explicitly named frame, matching `StaticSphere`.

Both item variants repeat `frame_id` for explicit consumer validation. In this proposal the value must equal `frame.frame_id`; the Environment source does not currently model a hierarchy of render frames. An unknown or mismatching frame is invalid, not a cue for the renderer to infer a transform.

## 3. Identity and deterministic digest

- `environment_id` and `environment_revision` are copied exactly from `StaticPhysicalScene`; they identify the owner scene revision, not a World run or causal cut.
- `render_geometry_sha256` is a lowercase 64-hex SHA-256 digest over the canonical JSON bytes of the object formed by removing only `render_geometry_sha256` from the descriptor. The digest includes `schema_version`, Environment identity/revision, units, complete frame descriptor and all items.
- Canonicalization is proposed as JSON Canonicalization Scheme (JCS, RFC 8785). The emitted/transmitted JSON need not itself be canonical, but producer and consumer MUST calculate the digest over JCS bytes. Before hashing, order `items` by ascending lexicographic order of each `object_id`'s UTF-8 byte sequence (compare unsigned bytes; if one sequence is a prefix of the other, the shorter sequence sorts first). This defines array order explicitly; JCS itself does not reorder array elements. Duplicate IDs reject before sorting/hash verification.
- Do not reuse the existing solver-oriented `geometry_revision`: it currently includes `gravity_m_s2` and `sliding_friction_coefficient`. Those fields and all other solver values are excluded here. Changing only gravity/friction must leave this render digest unchanged; changing an included display field must change it.
- This digest establishes descriptor integrity/equality only. It is not a signature, proof of owner authenticity, proof of World authorization, or causal-cut evidence.

The empty example above has digest `022f7875e378b8d9196f13528af47723ffd352f70e379e404946acb3ddc41a9d` under the proposed digest rule. A one-sphere example with the same identity/frame and `sphere-a` at `[1, 0, 0]`, radius `0.25`, hashes to `d0cf99d58351cd91d5c716c3fb8553e54144cd63b418d16a57fb3eca6a4481d4`.

## 4. Proposed validity and size bounds

These are candidate limits for Owner review, not existing Environment guarantees:

| Constraint | Candidate bound |
| --- | --- |
| Frame descriptors | Exactly one per descriptor |
| Items | 0–128 total; at most 128 combined planes and spheres |
| Identity/revision/frame/object strings | Non-empty Unicode scalar string, at most 128 UTF-8 bytes, no C0/C1 control characters |
| Coordinates and dimensions | Finite IEEE-754 binary64 values; vectors have exactly 3 elements |
| Sphere radius | Strictly greater than zero |
| Plane normal | Unit length with absolute norm tolerance `1e-9`; offset finite |
| Frame basis | Each axis unit length, pairwise orthogonal, right-handed, absolute tolerance `1e-9`; `handedness="RIGHT_HANDED"`; `up_axis` one of `X`, `Y`, `Z` |
| Serialized descriptor | At most 65,536 UTF-8 bytes, measured on the complete JSON envelope |
| Observation boundary | Must remain within the existing Observation response cap; this proposal requests no increase |

Reject booleans where numbers are expected, NaN/infinity, duplicate IDs, unknown fields, unknown primitive tags, missing fields, invalid UTF-8/Unicode, frame mismatch, invalid unit labels, digest mismatch, count overflow, or serialized-size overflow. A decoder must reject duplicate JSON object keys before digest calculation. Candidate finite values are not clipped or normalized by the renderer. The only geometry-related rounding/tolerance is validation of the source-declared orthonormal/unit invariants.

The descriptor imposes no owner-independent physical magnitude ceiling on finite coordinates, offsets, or positive radii. A consumer must preflight every primitive against its actual rendering numeric representation and reject the entire descriptor as unrenderable if conversion or derived bounds produce non-finite values, if a positive radius converts to zero, or if the renderer's representation collapses a sphere's positive extent. It must not clip coordinates, clamp dimensions, silently omit an unrenderable item, or present a partial descriptor as complete. A consumer that cannot perform this preflight must reject the descriptor rather than assume it is renderable. These checks do not redefine Environment's physical validity limits.

The 128-item and 64-KiB limits are proposed conservative application bounds below Observation's current local bridge default `DEFAULT_MAX_RESPONSE_BYTES = 1_000_000` (Observation `http_bridge.py`). The bridge cap is configurable and applies to its encoded complete response, so 64 KiB is a per-descriptor ceiling, not a guarantee that a larger response containing other data will fit. These candidate bounds do not change Observation's total response, item family, or safety policy. If an owner's legitimate scene exceeds either limit, reject the descriptor and return to Environment Owner review; do not silently truncate or split it.

## 5. Conformance vectors

### Accept

1. The empty descriptor above, with the exact digest shown, represents an empty Environment layer.
2. A descriptor with one finite, positive-radius sphere in the declared frame is valid when its digest matches. The one-sphere digest above is a concrete vector.
3. A plane with unit normal `[0, 0, 1]`, offset `0`, and matching scene `frame_id` is valid. Its geometry means an infinite plane, not a finite ground slab.
4. Permuting input item order must produce the same canonical item order and digest after sorting by ascending unsigned UTF-8 byte sequence of unique `object_id` values, with shorter prefix values first.
5. Changing only gravity or friction in the source scene does not change this render projection or its digest because those fields are not present.

### Reject

1. Add an unmodeled `box`/mesh/asset item or any unknown field.
2. Repeat an `object_id`, omit any required frame property, or set an item's `frame_id` to a value other than the descriptor's `frame.frame_id`.
3. Provide a sphere radius of `0`, a negative radius, a non-finite coordinate, a boolean coordinate, or a vector with other than three values.
4. Provide plane normal `[0, 0, 2]`, a non-finite offset, or a frame whose axes are not unit/orthogonal/right-handed within the specified tolerance.
5. Modify an included value while retaining the old digest, or supply malformed/uppercase/non-64-character digest text.
6. Exceed 128 items, 128 UTF-8 bytes in a bounded identity field, or 65,536 serialized bytes; or provide values that the consumer cannot represent/render under the preflight rule above.
7. Include `gravity_m_s2`, friction, material, genesis seed/configuration, checkpoint bytes, resource scalar-field data, dynamic state, arbitrary asset URL, or any non-render solver parameter.

## 6. Visual review criterion

An independent reviewer compares the descriptor with its source `StaticPhysicalScene`: every supported source plane/sphere is shown once with the same ID and declared parameters; frame labels, axis convention, SI units, and empty-state meaning are visible; the infinite plane is not falsely described as bounded; and no other physical attributes or transforms are inferred. The review must not add geometry or alter the physical scenario. A rendered screenshot is a fidelity check only, not evidence of physics, causal association, or cross-domain frame compatibility.

## 7. Explicitly out of scope

- Environment runtime implementation, APIs, serialization adapters, new publication families, and Observation changes.
- Dynamic Environment objects/state; current proposal is static only.
- World/run/tick/cut identity, causal correlation, authentication or cross-owner joins.
- Embodiment geometry, shared/global frames, cross-domain transforms, or scene composition.
- Remote/external access, persistence/history, arbitrary assets, mesh loading, terrain/scene generation, or changes to the M1 profile.
- Any Frontend renderer implementation or claim of full Spatial Visualization V1 acceptance.

## 8. Owner decisions requested before implementation/publication

The Environment Owner must accept, amend or reject the concrete primitive/field shapes, explicit frame repetition for both item variants, ground-plane interpretation, environment/display digest boundary and JCS method, deterministic `object_id` array-order rule, field/count/byte bounds, consumer rejection rule for values not representable by the renderer, and visual fidelity criterion. Acceptance of the design base or this candidate does not itself authorize implementation, publication, transport changes or exposure outside the existing local passive boundary. Spatial V1 registry status remains `proposed / not_evaluated / UNRESOLVED` until separately changed by the competent process.

## Evidence references

- Environment `src/environment/static_scene.py`: `FrameDescriptor`, `StaticGroundPlane`, `StaticSphere`, `StaticPhysicalScene`, and `_geometry_revision`.
- Environment `tests/test_static_scene.py` and `tests/test_environment_physical_projection.py`: frame/primitive validation, deterministic scene projection, and solver projection digest behavior.
- World `src/world/m1_profile.py` at `51cea9f8975fbdea603592fa5e9c56b073a2f4d4`, lines 479–482: M1 constructs `StaticPhysicalScene(..., objects=())`.
- Observation `src/observation/http_bridge.py` at `a8b43af65b79ca4e2455bfc1ff1b55faf3d4d353`, line 56: default maximum complete response is 1,000,000 bytes; the configured value can differ.
- RFC 8785 defines JCS canonical JSON used by the proposed digest; selecting JCS here remains an Environment Owner decision.
