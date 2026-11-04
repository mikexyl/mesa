#pragma once
// Plain interface to AMM-PGO# (MurpheyLab/DPGO). It is compiled into its own shared
// library with hidden symbols, so its Eigen build never mixes with GTSAM's.
#include <cstddef>
#include <vector>

#define AMM_BRIDGE_API __attribute__((visibility("default")))

namespace amm_bridge {
struct Edge {
  int i_node, i_pose, j_node, j_pose;  // 0-based node and node-local pose
  double R[9];                         // row-major relative rotation
  double t[3];                         // relative translation
  double kappa, tau;                   // rotational and translational precision
};

class AMM_BRIDGE_API Solver {
 public:
  // poses[a] lists node a's initial poses as (t[3], row-major R[9]) per pose. With
  // distributed_init their values are replaced by the authors' distributed chordal
  // initialization (only the pose counts are used).
  Solver(const std::vector<Edge>& edges, const std::vector<std::vector<double>>& poses, bool distributed_init);
  ~Solver();
  Solver(const Solver&) = delete;
  Solver& operator=(const Solver&) = delete;
  void iterate();  // one synchronous round: iterate, communicate, update
  std::vector<double> estimate(int node) const;  // same layout as the input poses
  size_t bytesPerRound() const;  // 8-byte key + float32 translation and rotation per received boundary pose
  size_t initializationBytes() const;  // payload before round 1: distributed init (if used) and starting poses
  size_t communicationEdges() const;

 private:
  struct Impl;
  Impl* impl_;
};
}  // namespace amm_bridge
