#!/usr/bin/env python3
"""Integration tests for native CBS through MESA's unchanged experiment CLI."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import gtsam
import jrl
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=True)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def fixture(name, dim=3, robots=('a', 'z'), connected=True, anchored=True, transform=None, unsupported=False):
    pose_type = gtsam.Pose3 if dim == 3 else gtsam.Pose2
    pose_tag = jrl.Pose3Tag if dim == 3 else jrl.Pose2Tag
    prior_tag = jrl.PriorFactorPose3Tag if dim == 3 else jrl.PriorFactorPose2Tag
    between_tag = jrl.BetweenFactorPose3Tag if dim == 3 else jrl.BetweenFactorPose2Tag
    prior_cls = gtsam.PriorFactorPose3 if dim == 3 else gtsam.PriorFactorPose2
    between_cls = gtsam.BetweenFactorPose3 if dim == 3 else gtsam.BetweenFactorPose2
    builder = jrl.DatasetBuilder(name, list(robots))
    keys, truth = {}, {}
    for r, robot in enumerate(robots):
        keys[robot] = [gtsam.symbol(robot, (1 << 49) + i) for i in range(5)]
        for i, key in enumerate(keys[robot]):
            if dim == 3:
                p = gtsam.Pose3(gtsam.Rot3.RzRyRx(.03*i, .02*r, .2*i), np.array([10+i, 20+3*r, .1*i]))
            else:
                p = gtsam.Pose2(10+i, 20+3*r, .2*i)
            truth[key] = transform.compose(p) if transform is not None else p
    d = 6 if dim == 3 else 3
    matrix = np.eye(d) * .03
    matrix[0, -1] = matrix[-1, 0] = .003
    noise = gtsam.noiseModel.Gaussian.Covariance(matrix)
    for r, robot in enumerate(robots):
        graph, tags, members = gtsam.NonlinearFactorGraph(), [], set(keys[robot])
        if anchored and (r == 0 or not connected):
            key = keys[robot][0]
            graph.add(prior_cls(key, truth[key], noise)); tags.append(prior_tag)
        for a, b in zip(keys[robot][:-1], keys[robot][1:]):
            graph.add(between_cls(a, b, truth[a].between(truth[b]), noise)); tags.append(between_tag)
        if connected:
            for neighbor in [r-1, r+1]:
                if 0 <= neighbor < len(robots):
                    for i in [1, 4]:
                        a, b = keys[robot][i], keys[robots[neighbor]][i]
                        # Reverse half the endpoints to exercise key ordering.
                        if i == 4: a, b = b, a
                        graph.add(between_cls(a, b, truth[a].between(truth[b]), noise)); tags.append(between_tag)
                        members.update([a, b])
        if unsupported:
            a,b=keys[robot][:2]
            graph.add(gtsam.RangeFactorPose3(a,b,1.,gtsam.noiseModel.Isotropic.Sigma(1,.1)))
            tags.append(jrl.RangeFactorPose3Tag)
        init, gt, types = gtsam.Values(), gtsam.Values(), {}
        for key in sorted(members):
            value=truth[key]
            # Deliberate shape error, while retaining exact measurements.
            if key == keys[robot][2]:
                delta=np.zeros(d);delta[-1]=.15;delta[0]=.02
                value=value.retract(delta)
            init.insert(key,value);gt.insert(key,truth[key]);types[key]=pose_tag
        builder.addEntry(robot,0,graph,tags,{},jrl.TypedValues(init,types),jrl.TypedValues(gt,types))
    path=root/(name+'.jrl')
    jrl.Writer().writeDataset(builder.build(),str(path),False)
    return path, truth, keys

def execute(path, dim=3, method='cbs', extra=(), expect_error=None):
    out=root/(path.stem+'-'+method+('-invalid' if extra else ''))
    out.mkdir()
    cmd=['run-dist-batch','-i',str(path),'-m',method,'-o',str(out)]
    if dim==3:cmd.append('--is3d')
    cmd.extend(extra)
    with (out/'run.log').open('w') as log:
        completed=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    if expect_error:
        assert completed.returncode != 0
        assert expect_error in (out/'run.log').read_text()
        return None
    assert completed.returncode==0, (cmd,(out/'run.log').read_text()[-4000:])
    files=list(out.glob('*/final_results.jrr.cbor'));assert len(files)==1
    result=jrl.Parser().parseResults(str(files[0]),True)
    return files[0].parent,result

summary={}
reference_result=None
for name,dim,robots,connected in [
        ('pose3-chain',3,('a','m','z'),True),
        ('pose2-chain',2,('a','z'),True),
        ('disconnected',3,('a','z'),False)]:
    path,truth,keys=fixture(name,dim,robots,connected)
    folder,result=execute(path,dim)
    status=json.loads((folder/'cbs-status.json').read_text())
    imports=json.loads((folder/'cbs-import.json').read_text())
    original=jrl.Parser().parseDataset(str(path),False)
    maximum=0
    for robot,typed in result.robot_solutions.items():
        expected=original.initialization(robot)
        assert set(typed.values.keys())==set(expected.keys())
        for key in typed.values.keys():
            p=typed.values.atPose3(key) if dim==3 else typed.values.atPose2(key)
            assert np.isfinite(p.matrix()).all()
            maximum=max(maximum,float(np.linalg.norm(truth[key].localCoordinates(p))))
        assert abs(imports[robot]['input_error']-imports[robot]['lifted_error'])<1e-6
        assert len(imports[robot]['key_mapping'])==len(expected.keys())
    assert status['all_world_references_available'],status
    assert status['converged'],status
    assert maximum < .08, (name,maximum,folder)
    assert len(status['components'])==(1 if connected else len(robots))
    communication=np.loadtxt(folder/'communication_counts.txt',ndmin=1)
    assert np.all(np.diff(communication)>=0)
    assert (communication[-1]>0)==connected
    summary[name]={'max_pose_error':maximum,'rounds':status['round'],'communications':int(communication[-1])}
    if name=='pose3-chain':reference_result=result

path,_,_=fixture('pose3-repeat',3,('a','m','z'))
_,repeated=execute(path)
repeat_error=max(np.linalg.norm(reference_result.robot_solutions[r].values.atPose3(k).localCoordinates(v.values.atPose3(k)))
                 for r,v in repeated.robot_solutions.items() for k in v.values.keys())
assert repeat_error<1e-9
summary['repeat_max_pose_difference']=float(repeat_error)

# A common rigid change of coordinates must preserve the solution and objective.
T=gtsam.Pose3(gtsam.Rot3.RzRyRx(.2,-.1,.7),np.array([42.,-13.,8.]))
path,truth,keys=fixture('transformed',3,('a','m','z'),transform=T)
folder,result=execute(path)
for typed in result.robot_solutions.values():
    for key in typed.values.keys():
        assert np.linalg.norm(truth[key].localCoordinates(typed.values.atPose3(key))) < .08
summary['common_frame_invariance']='passed'

path,_,_=fixture('unsupported',unsupported=True)
execute(path,expect_error='unsupported factors are never discarded')
path,_,_=fixture('unanchored',anchored=False)
execute(path,expect_error='no physical prior')
path,_,_=fixture('linear-rejection')
execute(path,extra=('--linear',),expect_error='not linear Point2/Point3')
summary['unsupported_and_unanchored_inputs']='explicitly rejected'

# An existing MESA method remains callable in the CBS-enabled build.
path,truth,keys=fixture('centralized-control')
folder,result=execute(path,method='centralized')
maximum=max(np.linalg.norm(truth[key].localCoordinates(v.values.atPose3(key)))
            for v in result.robot_solutions.values() for key in v.values.keys())
assert maximum<1e-4
summary['centralized_control_max_pose_error']=float(maximum)
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
