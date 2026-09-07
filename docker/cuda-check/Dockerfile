# =============================================================================
#  cuda-check - proves a CUDA kernel executes through the CDI path, not just
#  that nvidia-smi answers (see docker/cuda-check/check.cu for why that
#  distinction matters).
#
#  Multi-stage: nvcc and the rest of the CUDA devel toolchain (~a few GB) only
#  exist in the build stage. The shipped image carries the CUDA runtime and a
#  single compiled binary - small enough to be reusable in CI and in M5 chaos
#  testing without repeating the cost of the devel image.
# =============================================================================
ARG CUDA_TAG=12.8.1

FROM nvidia/cuda:${CUDA_TAG}-devel-ubuntu24.04 AS build
WORKDIR /src
COPY check.cu .
# sm_86 = compute capability 8.6 (RTX 3050 / Ampere), confirmed via
# `nvidia-smi --query-gpu=compute_cap` on the target host.
RUN nvcc -O2 -arch=sm_86 -o cuda-check check.cu

FROM nvidia/cuda:${CUDA_TAG}-base-ubuntu24.04 AS final
COPY --from=build /src/cuda-check /usr/local/bin/cuda-check
ENTRYPOINT ["/usr/local/bin/cuda-check"]
