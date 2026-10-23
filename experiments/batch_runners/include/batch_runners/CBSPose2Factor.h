#pragma once
#include <gtsam/base/numericalDerivative.h>
#include <gtsam/nonlinear/NonlinearFactor.h>
#include <cbs/utils/graph_partition.h>

namespace batch_runners {
/** Preserve GTSAM 4.2's Pose2 chart residual when CBS stores planar Pose3s.
 * The native Pose3 logarithm is not identical to Pose2::localCoordinates in
 * this GTSAM build. The remaining three residuals constrain only out-of-plane
 * motion, using the same lifted covariance as CBS's existing SE2 support.
 */
class CBSPose2Factor : public gtsam::NoiseModelFactor2<gtsam::Pose3,gtsam::Pose3> {
 public:
  CBSPose2Factor(gtsam::Key first,gtsam::Key second,const gtsam::Pose2& measured,
                 const gtsam::SharedNoiseModel& noise)
      :gtsam::NoiseModelFactor2<gtsam::Pose3,gtsam::Pose3>(extendNoiseModel(noise),first,second),measured_(measured) {}
  gtsam::Vector evaluateError(const gtsam::Pose3& first,const gtsam::Pose3& second,
      boost::optional<gtsam::Matrix&> H1=boost::none,boost::optional<gtsam::Matrix&> H2=boost::none) const override {
    std::function<gtsam::Vector6(const gtsam::Pose3&,const gtsam::Pose3&)> error=
        [this](const auto& a,const auto& b){return residual(a,b);};
    if(H1)*H1=gtsam::numericalDerivative21<gtsam::Vector6,gtsam::Pose3,gtsam::Pose3>(error,first,second);
    if(H2)*H2=gtsam::numericalDerivative22<gtsam::Vector6,gtsam::Pose3,gtsam::Pose3>(error,first,second);
    return residual(first,second);
  }
  gtsam::NonlinearFactor::shared_ptr clone() const override {
    return boost::make_shared<CBSPose2Factor>(*this);
  }
 private:
  gtsam::Vector6 residual(const gtsam::Pose3& first,const gtsam::Pose3& second) const {
    const auto e2=measured_.localCoordinates(pose3ToPose2(first).between(pose3ToPose2(second)));
    gtsam::Vector6 result=gtsam::Pose3::Logmap(pose2ToPose3(measured_).between(first.between(second)));
    result(2)=e2(2);result(3)=e2(0);result(4)=e2(1);
    return result;
  }
  gtsam::Pose2 measured_;
};
}
