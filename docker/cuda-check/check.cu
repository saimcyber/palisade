/*
 * Palisade M1 - prove CUDA *compute*, not just device visibility.
 *
 * `nvidia-smi` (M0's gpu-check) only proves the driver answers an NVML query.
 * It never launches a kernel, never touches the compiler toolchain, and would
 * pass even if the CDI spec were missing something a real workload needs.
 *
 * This program allocates two vectors on the device, launches a real kernel,
 * copies the result back, and verifies every element numerically. It exits
 * non-zero on any CUDA API error or on a wrong answer - "ran" is not "passed".
 */
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CUDA_CHECK(call)                                                     \
    do {                                                                     \
        cudaError_t _e = (call);                                             \
        if (_e != cudaSuccess) {                                             \
            fprintf(stderr, "CUDA ERROR %s:%d: %s\n", __FILE__, __LINE__,    \
                    cudaGetErrorString(_e));                                 \
            return 1;                                                       \
        }                                                                     \
    } while (0)

__global__ void vectorAdd(const float *a, const float *b, float *c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        c[i] = a[i] + b[i];
    }
}

int main(void) {
    const int n = 1 << 20; /* ~1M elements */
    const size_t bytes = static_cast<size_t>(n) * sizeof(float);

    printf("======================================================\n");
    printf(" Palisade M1 - CUDA compute through the CDI path\n");
    printf("======================================================\n");

    int deviceCount = 0;
    CUDA_CHECK(cudaGetDeviceCount(&deviceCount));
    if (deviceCount < 1) {
        fprintf(stderr, "FAIL: no CUDA devices visible\n");
        return 1;
    }

    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
    printf("device:            %s\n", prop.name);
    printf("compute capability: %d.%d\n", prop.major, prop.minor);
    printf("elements:          %d\n", n);
    printf("\n");

    std::vector<float> h_a(n), h_b(n), h_c(n);
    for (int i = 0; i < n; ++i) {
        h_a[i] = static_cast<float>(i);
        h_b[i] = static_cast<float>(2 * i);
    }

    float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
    CUDA_CHECK(cudaMalloc(&d_a, bytes));
    CUDA_CHECK(cudaMalloc(&d_b, bytes));
    CUDA_CHECK(cudaMalloc(&d_c, bytes));

    CUDA_CHECK(cudaMemcpy(d_a, h_a.data(), bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b.data(), bytes, cudaMemcpyHostToDevice));

    const int threadsPerBlock = 256;
    const int blocksPerGrid = (n + threadsPerBlock - 1) / threadsPerBlock;
    vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, n);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(h_c.data(), d_c, bytes, cudaMemcpyDeviceToHost));

    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_c);

    for (int i = 0; i < n; ++i) {
        float expected = h_a[i] + h_b[i];
        if (h_c[i] != expected) {
            fprintf(stderr, "FAIL: mismatch at %d: got %f, expected %f\n", i,
                    h_c[i], expected);
            return 1;
        }
    }

    printf("PASS: %d elements verified - a real CUDA kernel executed and\n", n);
    printf("      produced the correct numeric result through the CDI path.\n");
    return 0;
}
