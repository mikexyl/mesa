add_library(batch_runners INTERFACE)
target_link_libraries(batch_runners INTERFACE gtsam jrl mesa distributed-mapper admm DPGO)
target_include_directories(batch_runners INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/include")

option(MESA_WITH_CBS "Build the native CBS experiment runner" OFF)
if(MESA_WITH_CBS)
  find_package(cbs REQUIRED)
  add_library(cbs_runner STATIC CBSRunner.cpp)
  target_link_libraries(cbs_runner PUBLIC cbs jrl gtsam)
  target_include_directories(cbs_runner PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include")
  target_link_libraries(batch_runners INTERFACE cbs_runner)
  target_compile_definitions(batch_runners INTERFACE MESA_WITH_CBS=1)
endif()

# AMM-PGO# (MurpheyLab/DPGO), built separately as static archives. amm_bridge wraps it in a
# shared library with hidden symbols: its Eigen and namespace DPGO stay out of GTSAM and the
# ASAPP runner's dpgo, and only a plain std::vector interface crosses the boundary.
option(MESA_WITH_AMM "Build the AMM-PGO experiment runner" OFF)
if(MESA_WITH_AMM)
  set(AMM_ROOT "" CACHE PATH "MurpheyLab/DPGO C++ source directory")
  set(AMM_BUILD "" CACHE PATH "Build directory holding its static libraries in lib/")
  find_package(OpenMP REQUIRED)
  find_package(BLAS REQUIRED)
  find_package(LAPACK REQUIRED)
  add_library(amm_bridge SHARED amm_bridge/amm_bridge.cpp)
  # Same flags as the archives; the library's SO(d) projection uses AVX intrinsics.
  target_compile_options(amm_bridge PRIVATE -mavx2 -mfma -fvisibility=hidden -fvisibility-inlines-hidden)
  target_include_directories(amm_bridge PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/amm_bridge")
  target_include_directories(amm_bridge PRIVATE ${AMM_ROOT}/DPGO/include ${AMM_ROOT}/DChordal/include
      ${AMM_ROOT}/SESync/include ${AMM_ROOT}/Optimization/include ${AMM_ROOT}/PCM/include
      ${AMM_ROOT}/Preconditioners/Preconditioners/ILDL/include ${AMM_ROOT}/Preconditioners/Preconditioners/LSChol/include
      /usr/include/eigen3 /usr/include/suitesparse)
  file(GLOB AMM_ARCHIVES ${AMM_BUILD}/lib/*.a)
  target_link_libraries(amm_bridge PRIVATE -Wl,--start-group ${AMM_ARCHIVES} -Wl,--end-group
      spqr cholmod ${LAPACK_LIBRARIES} ${BLAS_LIBRARIES} glog OpenMP::OpenMP_CXX)
  target_link_options(amm_bridge PRIVATE -Wl,--exclude-libs,ALL -Wl,-Bsymbolic)
  add_library(amm_runner STATIC AMMRunner.cpp)
  target_include_directories(amm_runner PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include")
  target_link_libraries(amm_runner PUBLIC amm_bridge jrl gtsam)
  target_link_libraries(batch_runners INTERFACE amm_runner)
  target_compile_definitions(batch_runners INTERFACE MESA_WITH_AMM=1)
endif()
