add_library(batch_runners INTERFACE)
target_link_libraries(batch_runners INTERFACE gtsam jrl mesa admm)
target_include_directories(batch_runners INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/include")