#pragma once

#include "batch_runners/BatchRunner.h"
#include "batch_runners/CBSPose2Factor.h"
#include <cbs/bpsam/bpsam.h>
#include <cbs/bpsam/sharing_stage.h>
#include <cbs/utils/graph_partition.h>
#include <gtsam/slam/BetweenFactor.h>
#include <gtsam/slam/PriorFactor.h>
#include <nlohmann/json.hpp>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <set>
#include <type_traits>
#include <algorithm>
#include <optional>

namespace batch_runners {

/** Adapts native CBS to MESA's batch experiment lifecycle, without ROS or IPC.
 * Local solver gauges are separate from the physical priors in the JRL graph.
 * A shared virtual world pose carries those priors between robot-local frames.
 *
 * "cbs" keeps the phased offline schedule (pose rounds, then anchor rounds).
 * "cbs-persistent" follows CoLiBS's persistent async node (no PCM): every
 * receiver draws its own stage each round, pose-stage replies are not
 * forwarded, nobody is sent its own beliefs back, and pose keys a sender stops
 * answering are retracted.
 */
template<class Pose>
class CBSRunner final : public BatchRunner<Pose> {
  using Json=nlohmann::json;
  using Clock=std::chrono::steady_clock;
  struct Robot {
    char id;
    gtsam::Pose3 initial_frame;
    cbs::BPSAM::Ptr sam;
    std::map<gtsam::Key,gtsam::Key> keys;
    std::set<char> neighbors;
    std::optional<cbs::RandomStageSelector> stages;
    size_t physical_factors=0;
    double input_error=0;
    bool has_world_prior=false;
  };
 public:
  CBSRunner(jrl::Dataset dataset,std::string output,bool persistent=false)
      :BatchRunner<Pose>(persistent?"cbs-persistent":"cbs",dataset,output),persistent_(persistent) {
    // CoLiBS async node defaults (cbs_ros async_cbs_node.cpp).
    if(persistent_) {config_.erase("pose_rounds");config_.update(Json{{"d_max",0.3},{"pose_probability",0.5},{"seed",0}});}
    if(const char* path=std::getenv("MESA_CBS_CONFIG")) {
      std::ifstream input(path); if(!input)throw std::runtime_error("Cannot read MESA_CBS_CONFIG");
      Json supplied;input>>supplied;
      for(auto it=supplied.begin();it!=supplied.end();++it) {
        if(!config_.contains(it.key()))throw std::runtime_error("Unknown CBS setting: "+it.key());
        config_[it.key()]=it.value();
      }
    }
    if(persistent_!=config_.contains("pose_probability"))
      throw std::runtime_error("pose_probability/seed apply only to cbs-persistent; pose_rounds only to cbs");
    if(!persistent_ && config_.at("pose_rounds").get<int>()<1)throw std::runtime_error("Invalid CBS pose_rounds");
    if( config_.at("convergence_patience").get<int>()<1 ||
       !(config_.at("translation_epsilon").get<double>()>0) || !(config_.at("rotation_epsilon").get<double>()>0))
      throw std::runtime_error("Invalid CBS scheduling/convergence settings");
  }

  BatchIterResults init() override {
    const auto start=Clock::now();
    const auto robot_ids=this->dataset_.robots();
    if(robot_ids.empty())throw std::runtime_error("CBS requires at least one robot");
    const std::set<char> ids(robot_ids.begin(),robot_ids.end());
    if(ids.size()!=robot_ids.size() || ids.count('\0'))throw std::runtime_error("Duplicate or reserved robot ID");
    std::map<char,std::set<gtsam::Key>> original_keys;
    for(char id:robot_ids) {
      for(const auto& kv:this->dataset_.initialization(id)) {
        const char owner=gtsam::Symbol(kv.key).chr();
        if(!ids.count(owner))throw std::runtime_error("JRL key owner is absent from robot list");
        original_keys[owner].insert(kv.key);
      }
    }
    for(const auto& [id,keys]:original_keys) {
      size_t index=0;
      for(auto key:keys) rekey_[key]=cbs::toPoseKey(id,index++);
    }
    Json import=Json::object();
    for(char id:robot_ids) {
      Robot robot;robot.id=id;
      const auto initial=this->dataset_.initialization(id);
      gtsam::Key first=0;bool found=false;
      for(const auto& kv:initial) if(gtsam::Symbol(kv.key).chr()==id) {first=kv.key;found=true;break;}
      if(!found)throw std::runtime_error("Robot has no owned initialization poses");
      robot.initial_frame=lift(initial.template at<Pose>(first));
      gtsam::Values local;
      for(const auto& kv:initial) {
        const auto key=rekey_.at(kv.key);robot.keys[kv.key]=key;
        local.insert(key,robot.initial_frame.inverse()*lift(initial.template at<Pose>(kv.key)));
      }
      gtsam::NonlinearFactorGraph physical,original;
      for(const auto& entry:this->dataset_.measurements(id)) for(const auto& factor:entry.measurements) {
        if(!factor)throw std::runtime_error("Null input factor");
        for(auto key:factor->keys()) {
          if(!initial.exists(key))throw std::runtime_error("Missing initialization for input factor key");
          const char owner=gtsam::Symbol(key).chr();
          if(owner!=id)robot.neighbors.insert(owner);
        }
        if(auto prior=boost::dynamic_pointer_cast<gtsam::PriorFactor<Pose>>(factor)) {
          addBetween(physical,worldKey(),rekey_.at(prior->key()),prior->prior(),prior->noiseModel());
          robot.has_world_prior=true;
        } else if(auto between=boost::dynamic_pointer_cast<gtsam::BetweenFactor<Pose>>(factor)) {
          addBetween(physical,
              rekey_.at(factor->keys().at(0)),rekey_.at(factor->keys().at(1)),
              between->measured(),between->noiseModel());
        } else throw std::runtime_error("CBS MESA runner supports Pose2/Pose3 prior and between factors; unsupported factors are never discarded");
        original.push_back(factor);
      }
      if(robot.has_world_prior)local.insert(worldKey(),robot.initial_frame.inverse());
      robot.physical_factors=physical.size();
      robot.input_error=original.error(initial);
      const double lifted_error=physical.error(local);
      if(!std::isfinite(lifted_error) || std::abs(lifted_error-robot.input_error)>1e-6*(1+std::abs(robot.input_error)))
        throw std::runtime_error("CBS import changed the physical factor error");
      requireConnected(physical,local,rekey_.at(first));

      // These are gauge choices, not additional physical pose measurements.
      // The free world pose allows every original absolute prior to be optimized.
      const auto gauge=gtsam::noiseModel::Isotropic::Sigma(6,1e-4);
      physical.addPrior(cbs::toRobotKey(id),gtsam::Pose3(),gauge);
      physical.emplace_shared<gtsam::BetweenFactor<gtsam::Pose3>>(
          cbs::toRobotKey(id),rekey_.at(first),gtsam::Pose3(),gauge);
      local.insert(cbs::toRobotKey(id),gtsam::Pose3());
      cbs::BPSAM::Params params;params.robot_id=id;
      params.use_se2_beliefs=std::is_same<Pose,gtsam::Pose2>::value;
      params.gbp_update_params.d_min=config_.at("d_min");
      params.gbp_update_params.d_max=config_.at("d_max");
      params.gbp_update_params.target_hellinger=config_.at("target_hellinger");
      params.sam_params_.relinearizeSkip=1;
      params.sam_params_.cacheLinearizedFactors=false;
      params.sam_params_.findUnusedFactorSlots=true;
      params.sam_params_.setRelinearizeThreshold(0.01);
      params.sam_params_.optimizationParams=gtsam::ISAM2GaussNewtonParams();
      robot.sam=std::make_shared<cbs::BPSAM>(params);
      robot.sam->update(physical,local);
      if(persistent_)robot.stages.emplace(config_.at("pose_probability").get<double>(),
          config_.at("seed").get<uint32_t>(),static_cast<uint32_t>(id));
      Json mapping=Json::object();for(auto [original_key,key]:robot.keys)mapping[std::to_string(original_key)]=std::to_string(key);
      import[std::string(1,id)]={{"physical_factors",robot.physical_factors},{"gauge_factors",2},
          {"input_error",robot.input_error},{"lifted_error",lifted_error},{"key_mapping",mapping}};
      robots_.emplace(id,std::move(robot));
    }
    for(const auto& [id,robot]:robots_) for(char other:robot.neighbors)robots_.at(other).neighbors.insert(id);
    requireAnchoredComponents();
    std::ofstream(this->output_directory_+"/cbs-import.json")<<import.dump(2)<<'\n';
    auto result=results();previous_=globalOwned();
    record("initialization",0,0,0,seconds(start),0);
    return BatchIterResults(result,0);
  }

  BatchIterResults iterate() override {
    const auto start=Clock::now();++round_;
    // Stages are drawn before any exchange, so the schedule is seeded and
    // independent of iteration order. In phased mode every robot shares one stage.
    std::map<char,bool> pose_stage_of;
    for(auto& [id,robot]:robots_)
      pose_stage_of[id]=persistent_ ? robot.stages->next()==cbs::SharingStage::Pose
                                    : round_<=config_.at("pose_rounds").get<size_t>();
    const bool pose_stage=std::all_of(pose_stage_of.begin(),pose_stage_of.end(),[](const auto& s){return s.second;});
    std::map<char,cbs::BPSAM::Beliefs> inbox;
    std::map<std::pair<char,char>,gtsam::KeySet> requested_by;  // (receiver, sender) -> pose keys
    size_t packets=0,gaussians=0,skipped=0,retracted=0;
    for(auto& [id,robot]:robots_) {
      for(char receiver:robot.neighbors) {
        const bool pose=pose_stage_of.at(receiver);
        robot.sam->setMarginalizationGraph(pose ? cbs::BPSAM::MarginalizationType::LOCAL : cbs::BPSAM::MarginalizationType::GLOBAL);
        gtsam::KeySet requested;
        if(pose) {
          for(auto key:robots_.at(receiver).sam->allKeys())
            if(cbs::isPoseKey(key) && key!=worldKey())requested.insert(key);
          requested_by[{receiver,id}]=requested;
        } else {
          requested.insert(worldKey());
          for(const auto& [other,_]:robots_)requested.insert(cbs::toRobotKey(other));
        }
        // The persistent node forwards other robots' beliefs only in the anchor stage.
        const auto beliefs=robot.sam->getBeliefs(requested,!persistent_ || !pose);
        bool sent=false;
        for(const auto& [key,senders]:beliefs)for(const auto& [sender,belief]:senders) {
          if(persistent_ && sender==receiver)continue;  // never echo a requester's own beliefs
          ++gaussians;sent=true;
          inbox[receiver][key].emplace(sender,belief);
        }
        if(sent)++packets;
      }
      robot.sam->setMarginalizationGraph(cbs::BPSAM::MarginalizationType::FULL);
    }
    const double exchange=seconds(start);
    const auto update_start=Clock::now();
    for(auto& [id,robot]:robots_) {
      skipped+=robot.sam->addBeliefs(inbox[id]);
      if(persistent_) for(char sender:robot.neighbors) {
        // A requested pose key the sender no longer answers for is retracted.
        const auto found=requested_by.find({id,sender});
        if(found==requested_by.end())continue;
        gtsam::KeySet gone;
        for(auto key:found->second) {
          const auto belief=inbox[id].find(key);
          if(belief==inbox[id].end() || !belief->second.count(sender))gone.insert(key);
        }
        retracted+=robot.sam->removeBeliefs(sender,gone);
      }
      robot.sam->update();
    }
    auto owned=globalOwned();double translation=0,rotation=0;size_t count=0;
    for(const auto& [id,values]:owned)for(const auto& [key,pose]:values) {
      const auto& prev=previous_.at(id).at(key);
      translation+=(prev.translation()-pose.translation()).norm();
      rotation+=gtsam::Rot3::Logmap(prev.rotation().between(pose.rotation())).norm();++count;
    }
    previous_=std::move(owned);
    translation/=std::max(size_t(1),count);rotation/=std::max(size_t(1),count);
    // Persistent mode has no anchor-only phase: convergence needs stable
    // estimates once every robot has a world reference.
    const bool stable=(persistent_ || !pose_stage) && allWorldAvailable() &&
        translation<config_.at("translation_epsilon").get<double>() && rotation<config_.at("rotation_epsilon").get<double>();
    patience_=stable ? patience_+1 : 0;
    converged_=patience_>=config_.at("convergence_patience").get<size_t>();
    last_translation_=translation;last_rotation_=rotation;
    std::string phase=pose_stage?"pose":"anchor";
    if(persistent_){phase="";for(const auto& [id,pose]:pose_stage_of)phase+=std::string(1,id)+(pose?"P":"A");}
    record(phase,packets,gaussians,skipped,seconds(update_start),exchange,retracted);
    return BatchIterResults(results(),packets);
  }
  bool isConverged() override {return converged_;}

 private:
  static gtsam::Key worldKey() {return cbs::toPoseKey('\0',0);}
  static gtsam::Pose3 lift(const Pose& pose) {
    if constexpr(std::is_same<Pose,gtsam::Pose3>::value)return pose;
    else return pose2ToPose3(pose);
  }
  static Pose project(const gtsam::Pose3& pose) {
    if constexpr(std::is_same<Pose,gtsam::Pose3>::value)return pose;
    else return pose3ToPose2(pose);
  }
  static void addBetween(gtsam::NonlinearFactorGraph& graph,gtsam::Key first,gtsam::Key second,
                         const Pose& measured,const gtsam::SharedNoiseModel& model) {
    if constexpr(std::is_same<Pose,gtsam::Pose3>::value)
      graph.emplace_shared<gtsam::BetweenFactor<gtsam::Pose3>>(first,second,measured,model);
    else graph.emplace_shared<CBSPose2Factor>(first,second,measured,model);
  }
  static double seconds(Clock::time_point start) {return std::chrono::duration<double>(Clock::now()-start).count();}
  static void requireConnected(const gtsam::NonlinearFactorGraph& graph,const gtsam::Values& values,gtsam::Key first) {
    std::map<gtsam::Key,gtsam::KeySet> adjacency;
    for(const auto& factor:graph)for(auto a:factor->keys())for(auto b:factor->keys())adjacency[a].insert(b);
    gtsam::KeySet seen{first};std::vector<gtsam::Key> pending{first};
    while(!pending.empty()) {auto key=pending.back();pending.pop_back();for(auto next:adjacency[key])if(seen.insert(next).second)pending.push_back(next);}
    for(const auto& kv:values)if(!seen.count(kv.key))throw std::runtime_error("CBS local graph has disconnected or unused initialized poses; no synthetic support was added");
  }
  void requireAnchoredComponents() {
    std::set<char> seen;
    for(const auto& [id,_]:robots_)if(!seen.count(id)) {
      std::vector<char> pending{id};bool anchored=false;Json members=Json::array();seen.insert(id);
      while(!pending.empty()) {char next=pending.back();pending.pop_back();members.push_back(std::string(1,next));
        const auto& robot=robots_.at(next);anchored=anchored||robot.has_world_prior;
        for(char neighbor:robot.neighbors)if(seen.insert(neighbor).second)pending.push_back(neighbor);
      }
      if(!anchored)throw std::runtime_error("CBS component has no physical prior defining its JRL world frame");
      components_.push_back(members);
    }
  }
  bool allWorldAvailable() const {for(const auto& [_,r]:robots_)if(!r.sam->valueExists(worldKey()))return false;return true;}
  gtsam::Pose3 toWorld(const Robot& robot) const {
    return robot.sam->valueExists(worldKey()) ? robot.sam->template calculateEstimate<gtsam::Pose3>(worldKey()).inverse() : robot.initial_frame;
  }
  jrl::Results results() const {
    jrl::Results result(this->dataset_.name(),this->name_,this->dataset_.robots());
    for(const auto& [id,robot]:robots_) {
      const auto frame=toWorld(robot);gtsam::Values values;
      for(const auto& [original,key]:robot.keys) {
        const auto pose=frame*robot.sam->template calculateEstimate<gtsam::Pose3>(key);
        if(!pose.matrix().allFinite())throw std::runtime_error("Nonfinite CBS result");
        values.insert(original,project(pose));
      }
      result.robot_solutions[id]=jrl::TypedValues(values,this->dataset_.initializationWithTypes(id).types);
    }
    return result;
  }
  using Owned=std::map<char,std::map<gtsam::Key,gtsam::Pose3>>;
  Owned globalOwned() const {
    Owned result;
    for(const auto& [id,robot]:robots_)for(const auto& [original,key]:robot.keys)
      if(gtsam::Symbol(original).chr()==id)result[id][original]=toWorld(robot)*robot.sam->template calculateEstimate<gtsam::Pose3>(key);
    return result;
  }
  void record(const std::string& phase,size_t packets,size_t gaussians,size_t skipped,double update_s,double exchange_s,size_t retracted=0) {
    Json row={{"round",round_},{"phase",phase},{"directed_belief_packets",packets},{"gaussians",gaussians},
       {"skipped_beliefs",skipped},{"retracted_beliefs",retracted},{"mode",persistent_?"persistent":"phased"},{"update_s",update_s},{"exchange_s",exchange_s},
       {"all_world_references_available",allWorldAvailable()},{"converged",converged_},
       {"mean_translation_change",last_translation_},{"mean_rotation_change",last_rotation_},
       {"components",components_},{"config",config_},{"gtsam_version",GTSAM_VERSION_STRING}};
    std::ofstream(this->output_directory_+"/cbs-diagnostics.jsonl",std::ios::app)<<row.dump()<<'\n';
    std::ofstream(this->output_directory_+"/cbs-status.json")<<row.dump(2)<<'\n';
  }
  bool persistent_=false;
  Json config_={{"pose_rounds",41},{"convergence_patience",3},{"translation_epsilon",0.01},
      {"rotation_epsilon",0.001},{"d_min",0.0},{"d_max",0.1},{"target_hellinger",0.1}};
  Json components_=Json::array();
  std::map<char,Robot> robots_;
  std::map<gtsam::Key,gtsam::Key> rekey_;
  Owned previous_;
  size_t round_=0,patience_=0;
  bool converged_=false;
  double last_translation_=0,last_rotation_=0;
};
}  // namespace batch_runners
