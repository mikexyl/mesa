# CBS experiment runner

Build MESA with `-DMESA_WITH_CBS=ON -Dcbs_DIR=/path/to/cbs/lib/cmake/cbs`.
The CBS library must use **the same GTSAM 4.2 build as MESA**. The experiment
branch `codex/mesa-gtsam42` of `mikexyl/cbs` backports the current develop core
to that ABI. There is no worker process, ROS dependency, or alternate optimizer.

```sh
run-dist-batch -i example.jrl -m cbs -o results --is3d
# Omit --is3d for Pose2 graphs.
```

The runner implements MESA's `init`, `iterate`, `isConverged`, and normal JRR,
JRM, per-iteration, and communication-count outputs. Other methods retain their
existing factory branches and solver settings.

## Input and frame semantics

- Pose2 and Pose3 prior/between graphs are supported. The original per-robot
  factor allocation, measurement direction, covariance/noise model, owned and
  remote variables, and result type tags are preserved. Factor duplicates in
  the supplied JRL remain duplicates, as in the existing MESA runners.
- Robot IDs need not be contiguous. Original 64-bit keys are mapped bijectively
  to CBS labeled keys and restored on output; large indices are not truncated.
- Each robot has one native BPSAM instance. Its local frame is its first owned
  initialized pose. The identity robot anchor and its tie to that pose use
  CBS's native 1e-4 gauge sigma. These select a coordinate frame, without adding
  a physical global observation.
- A virtual world pose, reserved outside the dataset key mapping, preserves
  absolute input priors as world-to-pose factors. It is optimized, not fixed.
  Output is transformed by the estimated world pose, never by ground truth.
  The import checks the original physical graph error against the transformed
  graph before any optimization. A robot lacking a world estimate temporarily
  uses its input frame; diagnostics explicitly record incomplete references,
  and convergence is disabled until every world reference is available.
- Pose2 factors retain GTSAM 4.2's original chart residual. A small adapter
  factor embeds that residual into CBS's planar Pose3 state, with the same
  out-of-plane covariance used by native CBS. Its Jacobians use numerical
  derivatives; this additional cost applies to Pose2, not Pose3 experiments.
- Each local measurement graph must be connected and use every initialized
  pose. Each communication component needs a physical prior defining its
  dataset reference frame. Disconnected teams with their own priors remain
  disconnected. Unsupported factor families, linear Point2/Point3 problems,
  missing initialization, and unanchored components fail explicitly. No
  factors or robots are silently dropped.

## Scheduling and settings

One MESA iteration is one synchronous CBS round across all robots. The
communication topology is derived from foreign-key ownership in the input
factors, matching MESA's communication-edge convention. Messages are collected
before any receiving robot is updated. The first 41 rounds share pose beliefs
using native LOCAL marginalization; subsequent rounds share robot anchors and
the world reference using GLOBAL marginalization. This follows the phase split
of the develop offline example. It is an in-process batch simulation, not a
measurement of a deployed network.

The Hellinger controls retain the develop core defaults:
`d_min=0`, `d_max=0.1`, `target_hellinger=0.1`, merge type `Contract`.
iSAM2 uses the develop example's Gauss-Newton configuration, relinearization
skip 1 and threshold 0.01, with factor-slot reuse and no linear-factor cache.
Convergence means three consecutive anchor rounds with mean global owned-pose
translation change below 0.01 m and rotation change below 0.001 rad. It does
not establish optimality. The original MESA experiment iteration cap remains.

An optional JSON file selected by `MESA_CBS_CONFIG` may explicitly override
`pose_rounds`, `convergence_patience`, `translation_epsilon`, `rotation_epsilon`,
`d_min`, `d_max`, and `target_hellinger`. Unknown fields fail. The effective
configuration is saved with every run.

## Diagnostics and comparison limits

- `cbs-import.json`: reversible key maps, factor/gauge counts, and before/after
  import errors.
- `cbs-diagnostics.jsonl`: stages, iteration time, reference availability,
  components, convergence, packet/Gaussian counts, and skipped beliefs.
- `cbs-status.json`: final available status. Check this rather than treating a
  completed MESA run as a convergence claim.

`communication_counts.txt` counts nonempty **directed belief packets** for CBS;
one round can send two packets per neighbor edge. MESA's existing method counts
an activated robot pair per iteration. These native counts have different
granularity and must not be presented as equal-byte communication comparisons.
Detailed packet/Gaussian counts are retained; these are not network bandwidth.
Timing separates message preparation from update/result bookkeeping and
excludes MESA's external metric/file-writing costs.

Run the integration suite with:

```sh
python3 experiments/tests/test_cbs.py --output /new/empty/test-directory
```

It checks Pose2/Pose3, frame conversion, three-robot anchor propagation,
noncontiguous IDs, indices beyond CBS's native index bit range, repeated
execution, reverse endpoints, disconnected teams, explicit input rejection,
and the existing centralized runner. Native CBS tests remain in its own build.
