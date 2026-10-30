#pragma once
#include "batch_runners/BatchRunner.h"
#include <boost/shared_ptr.hpp>

namespace batch_runners {
// Keep CBS utility headers out of the other backends' translation unit.
template<class Pose>
boost::shared_ptr<BatchRunner<Pose>> makeCBSRunner(jrl::Dataset dataset,std::string output,bool persistent=false);
}
