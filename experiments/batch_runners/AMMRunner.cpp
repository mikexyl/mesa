// AMM-PGO# (Fan & Murphey, T-RO 2024; MurpheyLab/DPGO) in MESA's batch lifecycle.
// The solver lives behind amm_bridge, a shared library with hidden symbols, so
// its Eigen build and namespace DPGO never mix with GTSAM or the ASAPP runner's dpgo.
#include "batch_runners/AMMFactory.h"

#include <amm_bridge.h>
#include <gtsam/inference/Symbol.h>
#include <gtsam/slam/BetweenFactor.h>
#include <gtsam/slam/PriorFactor.h>

#include <boost/make_shared.hpp>
#include <fstream>
#include <algorithm>
#include <map>
#include <memory>
#include <stdexcept>

namespace batch_runners {

/** One MESA iteration is one synchronous AMM-PGO# round, as in the authors'
 * dist_pgo example: every node iterates, exchanges boundary poses, then updates.
 * Graph partition, factors and initial values come from the JRL, the same as
 * the other MESA runners. Priors only fix MESA's gauge; AMM-PGO is gauge-free
 * and does not use them. Each between factor's covariance becomes the method's
 * isotropic precisions, tau = 3/tr(Sigma_t) and kappa = 3/(2 tr(Sigma_R)),
 * as its own g2o reader does. "amm-pgo" starts from the JRL initialization like
 * the other runners; "amm-pgo-dinit" uses the authors' distributed chordal
 * initialization. Iteration 0 is charged with everything sent before round 1: the
 * distributed initialization if used and the neighbours' starting poses. Bytes use MESA's convention (8-byte key, float32 values):
 * 56 B per boundary pose a node receives per round in 3-D. */
template <class Pose>
class AMMRunner final : public BatchRunner<Pose> {
 public:
  AMMRunner(jrl::Dataset dataset, std::string output, bool distributed_init)
      : BatchRunner<Pose>(distributed_init ? "amm-pgo-dinit" : "amm-pgo", dataset, output),
        distributed_init_(distributed_init) {}

  BatchIterResults init() override {
    if (!std::is_same<Pose, gtsam::Pose3>::value) throw std::runtime_error("amm-pgo supports Pose3 graphs only");
    robots_ = this->dataset_.robots();
    const int nodes = robots_.size();
    owned_.resize(nodes);
    std::map<gtsam::Key, std::pair<int, int>> local;
    std::vector<std::vector<double>> poses(nodes);
    for (int a = 0; a < nodes; a++) {
      const char rid = robots_[a];
      const auto& initial = this->dataset_.initialization(rid);
      for (auto key : initial.keys())
        if (gtsam::Symbol(key).chr() == rid) owned_[a].push_back(key);
      std::sort(owned_[a].begin(), owned_[a].end());
      for (size_t i = 0; i < owned_[a].size(); i++) {
        local[owned_[a][i]] = {a, int(i)};
        const auto pose = initial.template at<gtsam::Pose3>(owned_[a][i]);
        append(poses[a], pose);
      }
    }

    std::vector<amm_bridge::Edge> edges;
    for (int a = 0; a < nodes; a++) {
      for (const auto& entry : this->dataset_.measurements(robots_[a])) {
        for (const auto& factor : entry.measurements) {
          if (boost::dynamic_pointer_cast<gtsam::PriorFactor<gtsam::Pose3>>(factor)) {
            ++priors_;
            continue;
          }
          auto between = boost::dynamic_pointer_cast<gtsam::BetweenFactor<gtsam::Pose3>>(factor);
          if (!between) throw std::runtime_error("amm-pgo supports Pose3 prior and between factors only");
          auto gaussian = boost::dynamic_pointer_cast<gtsam::noiseModel::Gaussian>(between->noiseModel());
          if (!gaussian) throw std::runtime_error("amm-pgo requires Gaussian between-factor noise");
          const gtsam::Matrix cov = gaussian->covariance();  // gtsam tangent order: rotation, translation
          const auto [i_node, i_pose] = local.at(between->key1());
          const auto [j_node, j_pose] = local.at(between->key2());
          amm_bridge::Edge e{i_node, i_pose, j_node, j_pose, {}, {}, 0, 0};
          const gtsam::Matrix3 R = between->measured().rotation().matrix();
          const gtsam::Vector3 t = between->measured().translation();
          for (int r = 0; r < 3; r++) {
            e.t[r] = t(r);
            for (int c = 0; c < 3; c++) e.R[3 * r + c] = R(r, c);
          }
          e.kappa = 3 / (2 * cov.topLeftCorner<3, 3>().trace());
          e.tau = 3 / cov.bottomRightCorner<3, 3>().trace();
          edges.push_back(e);
        }
      }
    }
    solver_ = std::make_unique<amm_bridge::Solver>(edges, poses, distributed_init_);
    std::ofstream(this->output_directory_ + "/amm-import.json")
        << "{\"between_factors\": " << edges.size() << ", \"priors_ignored\": " << priors_
        << ", \"communication_edges\": " << solver_->communicationEdges()
        << ", \"bytes_per_round\": " << solver_->bytesPerRound()
        << ", \"distributed_init\": " << (distributed_init_ ? "true" : "false")
        << ", \"initialization_bytes\": " << solver_->initializationBytes()
        << ", \"byte_model\": \"8-byte key + float32 translation and rotation per received boundary pose\"}\n";
    previous_ = estimate();
    // Traffic before round 1 (distributed initialization, starting poses) is charged to iteration 0.
    return BatchIterResults(results(previous_), 0, solver_->initializationBytes());
  }

  BatchIterResults iterate() override {
    solver_->iterate();
    const auto current = estimate();
    double dt = 0, dr = 0;
    for (const auto& [key, pose] : current) {
      const auto& before = previous_.at(key);
      dt += (pose.translation() - before.translation()).norm();
      dr += gtsam::Rot3::Logmap(before.rotation().between(pose.rotation())).norm();
    }
    dt /= current.size();
    dr /= current.size();
    patience_ = (dt < 0.01 && dr < 0.001) ? patience_ + 1 : 0;
    previous_ = current;
    return BatchIterResults(results(current), solver_->communicationEdges(), solver_->bytesPerRound());
  }

  // Same rule as the CBS runner: three rounds with mean owned-pose change below 1 cm and 1 mrad.
  bool isConverged() override { return patience_ >= 3; }

 private:
  static void append(std::vector<double>& out, const gtsam::Pose3& pose) {
    const gtsam::Matrix3 R = pose.rotation().matrix();
    for (int r = 0; r < 3; r++) out.push_back(pose.translation()(r));
    for (int r = 0; r < 3; r++)
      for (int c = 0; c < 3; c++) out.push_back(R(r, c));
  }

  std::map<gtsam::Key, gtsam::Pose3> estimate() const {
    std::map<gtsam::Key, gtsam::Pose3> poses;
    for (size_t a = 0; a < owned_.size(); a++) {
      const auto x = solver_->estimate(a);
      for (size_t i = 0; i < owned_[a].size(); i++) {
        const double* p = x.data() + 12 * i;
        gtsam::Matrix3 R;
        for (int r = 0; r < 3; r++)
          for (int c = 0; c < 3; c++) R(r, c) = p[3 + 3 * r + c];
        const gtsam::Vector3 t(p[0], p[1], p[2]);
        if (!R.allFinite() || !t.allFinite()) throw std::runtime_error("Nonfinite AMM-PGO estimate");
        poses[owned_[a][i]] = gtsam::Pose3(gtsam::Rot3::ClosestTo(R), t);
      }
    }
    return poses;
  }

  jrl::Results results(const std::map<gtsam::Key, gtsam::Pose3>& poses) const {
    jrl::Results result(this->dataset_.name(), this->name_, robots_);
    for (char rid : robots_) {
      const auto types = this->dataset_.initializationWithTypes(rid).types;
      gtsam::Values values;
      for (const auto& kv : types) values.insert(kv.first, poses.at(kv.first));
      result.robot_solutions[rid] = jrl::TypedValues(values, types);
    }
    return result;
  }

  std::vector<char> robots_;
  std::vector<std::vector<gtsam::Key>> owned_;
  bool distributed_init_;
  std::unique_ptr<amm_bridge::Solver> solver_;
  std::map<gtsam::Key, gtsam::Pose3> previous_;
  size_t priors_ = 0, patience_ = 0;
};

template <class Pose>
boost::shared_ptr<BatchRunner<Pose>> makeAMMRunner(jrl::Dataset dataset, std::string output, bool distributed_init) {
  return boost::make_shared<AMMRunner<Pose>>(dataset, output, distributed_init);
}
template boost::shared_ptr<BatchRunner<gtsam::Pose2>> makeAMMRunner<gtsam::Pose2>(jrl::Dataset, std::string, bool);
template boost::shared_ptr<BatchRunner<gtsam::Pose3>> makeAMMRunner<gtsam::Pose3>(jrl::Dataset, std::string, bool);
}  // namespace batch_runners
