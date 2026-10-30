#include "batch_runners/CBSFactory.h"
#include "batch_runners/CBSRunner.h"
#include <boost/make_shared.hpp>

namespace batch_runners {
template<class Pose>
boost::shared_ptr<BatchRunner<Pose>> makeCBSRunner(jrl::Dataset dataset,std::string output,bool persistent) {
  return boost::make_shared<CBSRunner<Pose>>(dataset,output,persistent);
}
template boost::shared_ptr<BatchRunner<gtsam::Pose2>> makeCBSRunner<gtsam::Pose2>(jrl::Dataset,std::string,bool);
template boost::shared_ptr<BatchRunner<gtsam::Pose3>> makeCBSRunner<gtsam::Pose3>(jrl::Dataset,std::string,bool);
}
