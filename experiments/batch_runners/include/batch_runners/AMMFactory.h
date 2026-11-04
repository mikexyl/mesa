#pragma once
#include "batch_runners/BatchRunner.h"
#include <boost/shared_ptr.hpp>

namespace batch_runners {
// Keep the AMM-PGO headers, whose namespaces are renamed at compile time, out of other runners.
template<class Pose>
boost::shared_ptr<BatchRunner<Pose>> makeAMMRunner(jrl::Dataset dataset,std::string output,bool distributed_init);
}
