cd /workspaces/src/gtsam/build
cmake .. -DGTSAM_BUILD_PYTHON=1 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
make -j8

cd /workspaces/src/jrl/build
cmake .. -DGTSAM_DIR=/workspaces/src/gtsam/build/ -DGTSAM_INCLUDE_DIR=/workspaces/src/gtsam/gtsam -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DJRL_BUILD_PYTHON=1
make -j8

cd /workspaces/src/mesa/build
cmake .. -Djrl_DIR=/workspaces/src/jrl/build -Djrl_INCLUDE_DIR=/workspaces/src/jrl/include -DGTSAM_DIR=/workspaces/src/gtsam/build -DGTSAM_INCLUDE_DIR=/workspaces/src/gtsam/gtsam -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
make -j8