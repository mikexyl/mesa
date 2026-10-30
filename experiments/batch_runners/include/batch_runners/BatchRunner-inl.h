#pragma once
#include <jrl/Writer.h>

#include <boost/filesystem.hpp>
#include <boost/format.hpp>
#include <ctime>
#include <iomanip>
#include <cstdlib>
#include <sstream>

#include "batch_runners/BatchRunner.h"

namespace bfs = boost::filesystem;

namespace batch_runners {
template <class POSE_TYPE>
void BatchRunner<POSE_TYPE>::optimize() {
  // Initialize the underlying method
  BatchIterResults current_estimate = init();

  // Setup local vars
  bool converged = false;
  size_t iter_count = 0;
  jrl::Writer result_writer;

  // Setup log for number of communications
  std::vector<size_t> cumulative_communications, cumulative_bytes;
  size_t total_communications = current_estimate.number_communications;
  size_t total_bytes = current_estimate.number_bytes;
  // Unified stopping: with MESA_RUN_TO_CAP=1 every method runs to the same harness cap and a
  // common rule is applied afterwards to the saved iterations.
  const char* run_to_cap_env = std::getenv("MESA_RUN_TO_CAP");
  const bool run_to_cap = run_to_cap_env && std::string(run_to_cap_env) == "1";

  // Save the Initial Results
  std::string prefix = (boost::format("%012d") % iter_count++).str();
  result_writer.writeResults(current_estimate.results, iteration_output_directory_ + "/" + prefix + ".jrr", true);
  jrl::MetricSummary metrics = jrl::metrics::computeMetricSummary<POSE_TYPE>(dataset_, current_estimate.results);
  result_writer.writeMetricSummary(metrics, iteration_output_directory_ + "/" + prefix + "_metrics.jrm", true);

  cumulative_communications.push_back(total_communications);
  cumulative_bytes.push_back(total_bytes);

  // Figure out the Max Iterations and Save Rate
  size_t save_rate = iterationsPerFullComms();
  size_t max_iters = 500 * dataset_.robots().size() * save_rate;

  while (!converged) {
    std::cout << "Iteration: " << iter_count << "---------------------------------------" << std::endl;
    // Run the iteration step
    BatchIterResults iter_results = iterate();

    // Update the total_number of communications
    total_communications += iter_results.number_communications;
    total_bytes += iter_results.number_bytes;

    // Save the intermediary results if step is correct
    if (iter_count % save_rate == 0) {
      std::string prefix = (boost::format("%012d") % iter_count).str();
      result_writer.writeResults(iter_results.results, iteration_output_directory_ + "/" + prefix + ".jrr", true);

      // If we are saving intermediate results compute and save their corresponding metrics
      // Compute the Metrics for this step
      metrics = jrl::metrics::computeMetricSummary<POSE_TYPE>(dataset_, iter_results.results);
      result_writer.writeMetricSummary(metrics, iteration_output_directory_ + "/" + prefix + "_metrics.jrm", true);

      // If we are saving intermediate results, record the current cumulative number of communications
      cumulative_communications.push_back(total_communications);
      cumulative_bytes.push_back(total_bytes);
    }

    // Update the current estimate
    current_estimate = iter_results;

    // Check for convergence
    converged = (!run_to_cap && isConverged()) || iter_count > max_iters;
    iter_count++;
  }

  // Save the Final results
  result_writer.writeResults(current_estimate.results, output_directory_ + "/final_results.jrr", true);

  // compute and save final metrics
  metrics = jrl::metrics::computeMetricSummary<POSE_TYPE>(dataset_, current_estimate.results);
  result_writer.writeMetricSummary(metrics, output_directory_ + "/final_metrics.jrm", true);

  // Write the cummulative communications
  // These are the communication counts for each intermediate result and the final results
  cumulative_communications.push_back(total_communications);
  std::ofstream comm_count_output_file(output_directory_ + "/communication_counts.txt");
  std::ostream_iterator<size_t> comm_output_iterator(comm_count_output_file, " ");
  std::copy(std::begin(cumulative_communications), std::end(cumulative_communications), comm_output_iterator);
  cumulative_bytes.push_back(total_bytes);
  std::ofstream byte_output_file(output_directory_ + "/communication_bytes.txt");
  std::ostream_iterator<size_t> byte_output_iterator(byte_output_file, " ");
  std::copy(std::begin(cumulative_bytes), std::end(cumulative_bytes), byte_output_iterator);
}

}  // namespace batch_runners