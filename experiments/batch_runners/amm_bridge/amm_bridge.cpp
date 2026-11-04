#include "amm_bridge.h"

#include <DChordal/DChordal.h>
#include <DChordal/DChordalReduced.h>
#include <DPGO/DPGOHash.h>
#include <DPGO/DPGO_utils.h>
#include <SESync/SESyncProblem.h>
#include <SESync/SESync_utils.h>

#include <memory>
#include <set>
#include <stdexcept>

namespace amm_bridge {
namespace {
constexpr int d = 3;

// Bytes follow MESA's convention for every runner: an 8-byte key plus float32 values.
// Boundary poses one node receives, k values per pose.
template <class Problem>
size_t pose_bytes(const Problem& problem, int k) {
  size_t poses = 0;
  for (const auto& [beta, received] : problem.index())
    if (beta != problem.node()) poses += received.size();
  return poses * (8 + k * 4);
}
template <class Problem>
size_t pose_bytes(const std::vector<std::shared_ptr<const Problem>>& problems, int k) {
  size_t bytes = 0;
  for (const auto& p : problems) bytes += pose_bytes(*p, k);
  return bytes;
}
// One k-value block from every neighbouring node (reduced stages), keyed by node.
template <class Problem>
size_t node_bytes(const Problem& problem, int k) {
  return problem.nn() * (8 + k * 4);
}

// The authors' distributed chordal initialization (examples/dist_pgo.cpp, --dist_init true),
// unchanged except for removed printing and the byte counters. Rotations then translations,
// each a reduced (node-level) stage and a full stage; node 0 anchors the reduced stages.
std::vector<DPGO::Matrix> distributedChordal(const std::vector<DPGO::measurements_t>& measurements,
                                             const std::vector<int>& owned, size_t& bytes) {
  const int nodes = measurements.size();
  int d = 3;
  std::vector<DPGO::Matrix> Xk(nodes);
    SESync::SESyncOpts SESyncOptions;
    SESyncOptions.verbose = false;

    std::vector<DChordal::Matrix> xs(nodes);

    for (int alpha = 0; alpha < nodes; alpha++) {
      int n = owned[alpha];

      SESync::SESyncResult result;
      DChordal::SESync(alpha, measurements[alpha], SESyncOptions, result);

      xs[alpha].noalias() =
          result.xhat.transpose() * result.xhat.middleCols(n, d);
    }

    std::vector<std::shared_ptr<DChordal::DChordalReduced_R>> dchordal_red_R(
        nodes);
    std::vector<std::shared_ptr<const DChordal::DChordalReducedProblem>>
        problems_red_R(nodes);
    DChordal::Options options;

    for (int alpha = 0; alpha < nodes; alpha++) {
      dchordal_red_R[alpha] = std::make_shared<DChordal::DChordalReduced_R>(
          alpha, measurements[alpha], options);

      problems_red_R[alpha] = dchordal_red_R[alpha]->problem();

      const auto &n = dchordal_red_R[alpha]->problem()->n();
      const auto &d = dchordal_red_R[alpha]->problem()->d();
      const auto &recv = dchordal_red_R[alpha]->problem()->recv();

      xs[alpha].conservativeResize((d + 1) * (n[0] + n[1]), d);
    }

    d = problems_red_R[0]->d();

    std::vector<DChordal::Matrix> rots_n(nodes);
    std::vector<DChordal::Matrix> rots(nodes);

    // rotation initialization

    DPGO::communicate(problems_red_R, xs);
    bytes += pose_bytes(problems_red_R, (d + 1) * d);

    for (int alpha = 0; alpha < nodes; alpha++) {
      const auto &d = problems_red_R[alpha]->d();

      dchordal_red_R[alpha]->setup(xs[alpha]);

      DChordal::Matrix R(d * problems_red_R[alpha]->nn() + d, d);

      for (int n = 0; n <= problems_red_R[alpha]->nn(); n++) {
        R.middleRows(d * n, d).setIdentity();
      }

      dchordal_red_R[alpha]->initialize(R);
    }

    for (int iter = 0; iter < 100; iter++) {
      auto fobj = DChordal::evaluate_f(dchordal_red_R);

      for (int alpha = 1; alpha < nodes; alpha++) {
        dchordal_red_R[alpha]->update();
        dchordal_red_R[alpha]->iterate();
      }

      for (int alpha = 0; alpha < nodes; alpha++) {
        dchordal_red_R[alpha]->n_communicate(dchordal_red_R);
        bytes += node_bytes(*problems_red_R[alpha], d * d);
      }
    }

    for (int alpha = 0; alpha < nodes; alpha++) {
      rots_n[alpha] = dchordal_red_R[alpha]->results().Xak;
      DChordal::project_to_SOd(rots_n[alpha], rots_n[alpha]);
    }
    std::vector<std::shared_ptr<DChordal::DChordal_R>> dchordal_R(nodes);
    std::vector<std::shared_ptr<const DChordal::DChordalProblem>> problems_R(
        nodes);

    for (int alpha = 0; alpha < nodes; alpha++) {
      dchordal_R[alpha] = std::make_shared<DChordal::DChordal_R>(
          alpha, measurements[alpha], options);

      problems_R[alpha] = dchordal_R[alpha]->problem();

      const auto &n = problems_R[alpha]->n();

      rots[alpha].setZero(d * (n[0] + n[1]), d);
      rots[alpha].topRows(d * n[0]).noalias() =
          xs[alpha].middleRows(n[0], d * n[0]) * rots_n[alpha];
    }

    for (int alpha = 0; alpha < nodes; alpha++) {
      const auto &s = problems_R[alpha]->s();

      for (const auto &info : problems_R[alpha]->index()) {
        int beta = info.first;

        if (beta == alpha)
          continue;

        for (const auto &index : info.second) {
          const auto &i = index.second;
          const auto &j = index.first;

          rots[alpha].middleRows(d * (s[1] + i[1]), d) =
              rots[beta].middleRows(d * j, d);
        }
      }
    }
    bytes += pose_bytes(problems_R, d * d);  // neighbours' rotations copied in

    for (int alpha = 0; alpha < nodes; alpha++) {
      dchordal_R[alpha]->setup();
      dchordal_R[alpha]->initialize(rots[alpha]);
    }

    for (int iter = 0; iter < 400; iter++) {
      auto fobj = DChordal::evaluate_f(dchordal_R);

      for (int alpha = 0; alpha < nodes; alpha++) {
        dchordal_R[alpha]->update();
        dchordal_R[alpha]->iterate();
      }

      for (int alpha = 0; alpha < nodes; alpha++) {
        dchordal_R[alpha]->communicate(dchordal_R);
        bytes += pose_bytes(*problems_R[alpha], d * d);
      }
    }

    for (int alpha = 0; alpha < nodes; alpha++) {
      const auto &n = problems_R[alpha]->n();

      rots[alpha] = dchordal_R[alpha]->results().Xak;

      if (d == 2) {
        DPGO::project_to_SO2n(rots[alpha], rots[alpha]);
      } else if (d == 3) {
        DPGO::project_to_SO3n(rots[alpha], rots[alpha]);
      } else {
        DPGO::project_to_SOdn(rots[alpha], rots[alpha]);
      }

      rots_n[alpha] = rots[alpha].topRows(d);

      xs[alpha].middleRows(n[0], d * n[0]).noalias() =
          rots[alpha].topRows(d * n[0]) * rots_n[alpha].transpose();
    }

    // translation initialization

    std::vector<std::shared_ptr<DChordal::DChordalReduced_t>> dchordal_red_t(
        nodes);
    std::vector<std::shared_ptr<const DChordal::DChordalReducedProblem>>
        problems_red_t(nodes);

    for (int alpha = 0; alpha < nodes; alpha++) {
      dchordal_red_t[alpha] = std::make_shared<DChordal::DChordalReduced_t>(
          alpha, measurements[alpha], options);

      problems_red_t[alpha] = dchordal_red_t[alpha]->problem();

      auto problem_t =
          std::dynamic_pointer_cast<const DChordal::DChordalReducedProblem_t>(
              problems_red_t[alpha]);

      const auto &n = problems_red_t[alpha]->n();

      auto t = xs[alpha].topRows(n[0]);
      auto R = xs[alpha].middleRows(n[0], d * n[0]);

      problem_t->recover_translations(R, t);
    }

    DPGO::communicate(problems_red_t, xs);
    bytes += pose_bytes(problems_red_t, (d + 1) * d);
    DChordal::n_communicate(problems_red_R, rots_n);
    for (const auto& p : problems_red_R) bytes += node_bytes(*p, d * d);

    for (int alpha = 0; alpha < nodes; alpha++) {
      DChordal::Matrix t =
          DChordal::Matrix::Zero(problems_red_t[alpha]->nn() + 1, d);

      dchordal_red_t[alpha]->setup(xs[alpha], rots_n[alpha]);
      dchordal_red_t[alpha]->initialize(t);
    }

    for (int iter = 0; iter < 150; iter++) {

      for (int alpha = 1; alpha < nodes; alpha++) {
        dchordal_red_t[alpha]->update();
        dchordal_red_t[alpha]->iterate();
      }

      for (int alpha = 0; alpha < nodes; alpha++) {
        dchordal_red_t[alpha]->n_communicate(dchordal_red_t);
        bytes += node_bytes(*problems_red_t[alpha], d);
      }
    }

    std::vector<std::shared_ptr<DChordal::DChordal_t>> dchordal_t(nodes);
    std::vector<std::shared_ptr<const DChordal::DChordalProblem>> problems_t(
        nodes);

    std::vector<DChordal::Matrix> ts(nodes);

    for (int alpha = 0; alpha < nodes; alpha++) {
      dchordal_t[alpha] = std::make_shared<DChordal::DChordal_t>(
          alpha, measurements[alpha], options);

      problems_t[alpha] = dchordal_t[alpha]->problem();
    }

    for (int alpha = 0; alpha < nodes; alpha++) {
      const auto &n = problems_t[alpha]->n();

      ts[alpha].noalias() = xs[alpha].topRows(n[0]) * rots_n[alpha].topRows(d);
      ts[alpha].rowwise() += dchordal_red_t[alpha]->results().Xak.row(0);
    }

    DChordal::communicate(problems_R, rots);
    bytes += pose_bytes(problems_R, d * d);
    DChordal::communicate(problems_t, ts);
    bytes += pose_bytes(problems_t, d);

    for (int alpha = 0; alpha < nodes; alpha++) {
      dchordal_t[alpha]->setup(rots[alpha]);
      dchordal_t[alpha]->initialize(ts[alpha]);
    }

    for (int iter = 0; iter < 250; iter++) {

      for (int alpha = 0; alpha < nodes; alpha++) {
        dchordal_t[alpha]->update();
        dchordal_t[alpha]->iterate();
      }

      for (int alpha = 0; alpha < nodes; alpha++) {
        dchordal_t[alpha]->communicate(dchordal_t);
        bytes += pose_bytes(*problems_t[alpha], d);
      }
    }

    for (int alpha = 0; alpha < nodes; alpha++) {
      const auto &n = problems_t[alpha]->n()[0];

      Xk[alpha].setZero((d + 1) * n, d);
      Xk[alpha].topRows(n) = dchordal_t[alpha]->results().Xak;
      Xk[alpha].bottomRows(d * n) = rots[alpha].topRows(d * n);
    }
  return Xk;
}
}  // namespace

struct Solver::Impl {
  std::vector<std::shared_ptr<DPGO::DPGOHash>> hashes;
  std::vector<int> n;
  size_t bytes = 0, edges = 0, init_bytes = 0;
};

Solver::Solver(const std::vector<Edge>& edges, const std::vector<std::vector<double>>& poses, bool distributed_init)
    : impl_(new Impl) {
  const int nodes = poses.size();
  std::vector<DPGO::measurements_t> measurements(nodes);
  for (const auto& e : edges) {
    DPGO::RelativePoseMeasurement m;
    m.i = DPGO::Index(e.i_node, e.i_pose);
    m.j = DPGO::Index(e.j_node, e.j_pose);
    m.R = Eigen::Map<const Eigen::Matrix<double, 3, 3, Eigen::RowMajor>>(e.R);
    m.t = Eigen::Map<const Eigen::Vector3d>(e.t);
    m.kappa = e.kappa;
    m.tau = e.tau;
    measurements[e.i_node].push_back(m);
    if (e.j_node != e.i_node) measurements[e.j_node].push_back(m);
  }

  DPGO::Options options;  // the authors' dist_pgo settings: accelerated, trivial loss
  options.rescale = DPGO::Rescale::Static;
  options.loss = DPGO::Loss::None;
  options.loss_reg = 0.25;
  options.verbose = false;
  options.scheme = DPGO::Scheme::AMM;
  options.STPCG_kappa = 0.05;
  options.STPCG_theta = 0.9;
  options.eta[0] = 5e-4;
  options.eta[1] = 2.5e-2;
  options.max_soft_restart_hits[0] = 10;
  options.max_soft_restart_hits[1] = 25;
  options.max_iterations = 10;
  options.max_iterations_accepted = 1;
  options.grad_norm_tol = 1e-3;
  options.preconditioned_grad_norm_tol = 1e-4;
  options.regularizer = 1e-11;

  auto& I = *impl_;
  std::vector<std::shared_ptr<const DPGO::DPGOProblem>> problems(nodes);
  std::vector<DPGO::Matrix> xs(nodes);
  I.hashes.resize(nodes);
  I.n.resize(nodes);
  for (int a = 0; a < nodes; a++) {
    I.hashes[a] = std::make_shared<DPGO::DPGOHash>(a, measurements[a], options);
    problems[a] = I.hashes[a]->problem();
    const int n = I.n[a] = poses[a].size() / 12;
    if (problems[a]->n()[0] != n) throw std::runtime_error("amm-pgo: every owned pose must appear in a factor of its robot");
    if (distributed_init) continue;
    xs[a].setZero((d + 1) * n, d);
    for (int i = 0; i < n; i++) {
      const double* p = poses[a].data() + 12 * i;
      xs[a].row(i) = Eigen::Map<const Eigen::RowVector3d>(p);
      xs[a].middleRows(n + d * i, d) = Eigen::Map<const Eigen::Matrix<double, 3, 3, Eigen::RowMajor>>(p + 3).transpose();
    }
  }
  if (distributed_init) xs = distributedChordal(measurements, I.n, I.init_bytes);
  DPGO::communicate(problems, xs);
  I.init_bytes += pose_bytes(problems, (d + 1) * d);  // neighbours' starting poses
  std::set<std::pair<int, int>> pairs;
  for (int a = 0; a < nodes; a++) {
    I.hashes[a]->initialize(xs[a]);
    I.hashes[a]->update();
    for (const auto& [beta, received] : problems[a]->index()) {
      if (beta == a) continue;
      I.bytes += received.size() * (8 + (d + 1) * d * 4);
      pairs.insert({std::min(a, beta), std::max(a, beta)});
    }
  }
  I.edges = pairs.size();
}

Solver::~Solver() { delete impl_; }

void Solver::iterate() {
  for (auto& hash : impl_->hashes) hash->iterate();
  for (auto& hash : impl_->hashes) hash->communicate(impl_->hashes);
  for (auto& hash : impl_->hashes) hash->update();
}

std::vector<double> Solver::estimate(int a) const {
  const auto& X = impl_->hashes.at(a)->results().Xk;
  const int n = impl_->n[a];
  std::vector<double> out(12 * n);
  for (int i = 0; i < n; i++) {
    double* p = out.data() + 12 * i;
    Eigen::Map<Eigen::RowVector3d> t(p);
    Eigen::Map<Eigen::Matrix<double, 3, 3, Eigen::RowMajor>> R(p + 3);
    t = X.row(i);
    R = X.middleRows(n + d * i, d).transpose();
  }
  return out;
}

size_t Solver::bytesPerRound() const { return impl_->bytes; }
size_t Solver::initializationBytes() const { return impl_->init_bytes; }
size_t Solver::communicationEdges() const { return impl_->edges; }
}  // namespace amm_bridge
