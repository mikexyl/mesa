
#include <ADMM.h>
#include <ADMMUtils.h>
#include <gtsam/geometry/Pose2.h>
#include <gtsam/geometry/Pose3.h>
#include <gtsam/slam/dataset.h>

int main(int argc, const char* argv[]) {
  // Read the g2o File
  bool is3D = true;
  //   get file_path from args
  std::string file_path = argc > 1 ? argv[1] : "data/2d/2d-1.g2o";
  gtsam::GraphAndValues readGraph = gtsam::readG2o(file_path, is3D);
  gtsam::NonlinearFactorGraph graph = *(readGraph.first);
  gtsam::Values initial = *(readGraph.second);

  // output current graph's error
  std::cout << "Initial Error: " << graph.error(initial) << std::endl;
  //   output factors' diff from node diff
  for (size_t i = 0; i < graph.size(); i++) {
    gtsam::NonlinearFactor::shared_ptr factor = graph[i];
    double e = factor->error(initial);
    std::cout << "--------------------------------------" << std::endl;
    std::cout << "Factor " << i << " error = " << e << std::endl;

    auto between = boost::dynamic_pointer_cast<gtsam::BetweenFactor<gtsam::Pose3>>(factor);
    if (between) {
      // The measured relative pose from the factor
      gtsam::Pose3 measured = between->measured();

      // Predicted relative pose from the initial estimate
      gtsam::Key key1 = between->key1();
      gtsam::Key key2 = between->key2();
      gtsam::Pose3 pose1 = initial.at<gtsam::Pose3>(key1);
      gtsam::Pose3 pose2 = initial.at<gtsam::Pose3>(key2);
      gtsam::Pose3 predicted = pose1.between(pose2);
      gtsam::Pose3 predicted_v2 = pose2.between(pose1);

      // Compute the "difference" between measured and predicted
      gtsam::Pose3 diff = measured.between(predicted);
      gtsam::Pose3 diff_v2 = measured.between(predicted_v2);
    //   print the node id and the translation and rotation difference
        std::cout << "Node " << key1 << " to " << key2 << std::endl;
      std::cout << "Translation difference: " << diff.translation().norm() << " Rotation difference: " << diff.rotation().xyz().norm() << std::endl;
      std::cout << "Translation difference v2: " << diff_v2.translation().norm() << " Rotation difference: " << diff_v2.rotation().xyz().norm() << std::endl;
    } else {
      std::cout << "Factor " << i << " is not a BetweenFactor<gtsam::Pose3>" << std::endl;
    }
  }
//   solve the graph using LM
    gtsam::LevenbergMarquardtParams params;
    params.setErrorTol(1e-8);
    params.setMaxIterations(1000);
    gtsam::LevenbergMarquardtOptimizer optimizer(graph, initial, params);
    gtsam::Values result = optimizer.optimize();
    std::cout << "Final Error: " << graph.error(result) << std::endl;
    return 0;
}
