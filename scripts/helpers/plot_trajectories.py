import gtsam
import numpy as np
import matplotlib.pyplot as plt


def plot_traj_2d(
    ax,
    dataset,
    results,
    colors,
    label="",
    include_gt=False,
    include_shared_vars=False,
    linear=False,
):
    for idx, robot in enumerate(dataset.robots()):
        if dataset.containsGroundTruth() and include_gt:
            gtx, gty = [], []
            gtvals = dataset.groundTruth(robot)
            for k in gtvals.keys():
                s = gtsam.Symbol(k)
                if chr(s.chr()) == robot:
                    if linear:
                        p = gtvals.atPoint2(k)
                        gtx.append(p[0])
                        gty.append(p[1])
                    else:
                        p = gtvals.atPose2(k)
                        gtx.append(p.x())
                        gty.append(p.y())
            ax.plot(gtx, gty, alpha=0.5, color=colors[idx])

        sx, sy = [], []
        ox, oy = [], []
        svals = results.robot_solutions[robot].values
        for k in svals.keys():
            s = gtsam.Symbol(k)
            if linear:
                p = svals.atPoint2(k)
            else:
                p = svals.atPose2(k)
                p = [p.x(), p.y()]
            if chr(s.chr()) == robot:
                sx.append(p[0])
                sy.append(p[1])
            else:
                ox.append(p[0])
                oy.append(p[1])

        ax.plot(sx, sy, alpha=1, color=colors[idx], label=label)

        if include_shared_vars:
            ax.plot(ox, oy, "o", color=colors[idx])


def plot_traj_3d(
    ax,
    dataset,
    results,
    colors,
    label="",
    include_gt=False,
    include_shared_vars=False,
    linear=False,
):
    for idx, robot in enumerate(dataset.robots()):
        if dataset.containsGroundTruth() and include_gt:
            gt = []
            gtvals = dataset.groundTruth(robot)
            for k in gtvals.keys():
                s = gtsam.Symbol(k)
                if chr(s.chr()) == robot:
                    if linear:
                        gt.append(gtvals.atPoint3(k))
                    else:
                        gt.append(gtvals.atPose3(k).translation())
            gt = np.stack(gt)
            ax.plot(gt.T[0], gt.T[1], gt.T[2], alpha=0.5, color=colors[idx])

        prev = np.zeros(3)
        sol = [[]]
        oth = []
        svals = results.robot_solutions[robot].values
        for k in svals.keys():
            s = gtsam.Symbol(k)
            if linear:
                p = svals.atPoint3(k)
            else:
                p = svals.atPose3(k).translation()
                if np.linalg.norm(prev - p) > 7:
                    sol.append([])
                prev = p
            if chr(s.chr()) == robot:
                sol[-1].append(p)
            else:
                oth.append(p)
        for partial_sol in sol:
            if len(partial_sol) >0:
                partial_sol = np.stack(partial_sol)
                if len(oth) > 0:
                    oth = np.stack(oth)
                ax.plot(partial_sol.T[0], partial_sol.T[1], partial_sol.T[2], alpha=1, color=colors[idx], label=label)

        if include_shared_vars and (len(oth) > 0):
            ax.plot(oth.T[0], oth.T[1], oth.T[2], "o", color=colors[idx])
        #ax.view_init(elev=90, azim=-90)

def save_results_to_txt(dataset, results, filename, linear=False):
    """
    Save each robot's trajectory from 'results' into a text file.
    
    Format per line:
    robot_id    key    w    x    y    z    tx    ty    tz
    
    - robot_id : single character identifying the robot
    - key      : integer key used in the GTSAM Symbol
    - w, x, y, z : quaternion components of the orientation
    - tx, ty, tz : translation (position) values
    """
    with open(filename, 'w') as f:
        # Optionally, write a header line:
        f.write("# robot key w x y z tx ty tz\n")

        # Loop through each robot in the dataset
        for robot in dataset.robots():
            # Extract the Values object for that robot
            svals = results.robot_solutions[robot].values

            # Loop through each key in the Values
            for k in svals.keys():
                symbol = gtsam.Symbol(k)

                # Only process if this key is indeed for this robot
                if chr(symbol.chr()) == robot:
                    if linear:
                        # If the solution is in Point3 format
                        point = svals.atPoint3(k)  # 3D point
                        # For a linear case, there's no orientation to extract,
                        # so you might store 'NaN' or skip orientation
                        f.write(f"{robot} {symbol.index()} NaN NaN NaN NaN {point[0]} {point[1]} {point[2]}\n")
                    else:
                        # Otherwise, the solution is assumed to be a Pose3
                        pose = svals.atPose3(k)
                        # Extract quaternion (as w, x, y, z)
                        rotation_quat = pose.rotation().toQuaternion()
                        w, x, y, z = rotation_quat.w(), rotation_quat.x(), rotation_quat.y(), rotation_quat.z()
                        # Extract translation
                        tx, ty, tz = pose.translation()
                        
                        # Write a line in the desired format
                        f.write(f"{robot} {symbol.index()} {w:.9f} {x:.9f} {y:.9f} {z:.9f} {tx:.9f} {ty:.9f} {tz:.9f}\n")
