// ===========================================================================
//  CUDA Matrix Multiplication: C (M x N) = A (M x K) * B (K x N)
//
//  Two GPU kernels are compared:
//    1. matmul_naive  : each thread computes one C element directly from
//                       global memory. No data reuse across threads.
//    2. matmul_shared : tiled kernel using shared memory. Threads in a
//                       block cooperatively load tiles of A and B into
//                       shared memory, then reuse them for multiple MACs.
//
//  Correctness is verified by comparing the two GPU results element-wise.
//
//  Build:   nvcc -O3 -std=c++17 matmul.cu -o matmul
//  Run:     ./matmul                 # default 2048 x 2048 x 2048
//           ./matmul M N K           # custom dims
// ===========================================================================

#include <cuda_runtime.h>
#include <iostream>
#include <iomanip>
#include <cstdlib>
#include <cstdio>
#include <cmath>
#include <algorithm>

// Tile size for shared-memory kernel; must equal the block dim.
#define TILE 32

// ---------------------------------------------------------------------------
//  CUDA error-check macro
// ---------------------------------------------------------------------------
#define CHECK_CUDA(call)                                                       \
    do {                                                                       \
        cudaError_t err__ = (call);                                            \
        if (err__ != cudaSuccess) {                                            \
            std::fprintf(stderr, "CUDA error %s:%d: %s\n",                     \
                         __FILE__, __LINE__, cudaGetErrorString(err__));       \
            std::exit(EXIT_FAILURE);                                           \
        }                                                                      \
    } while (0)

// ---------------------------------------------------------------------------
//  Naive kernel: one thread -> one C element
//    C has shape (M rows, N cols). Each thread reads K elements from A and
//    K elements from B, all from global memory.
// ---------------------------------------------------------------------------
__global__ void matmul_naive(const float* __restrict__ A,
                             const float* __restrict__ B,
                             float* __restrict__ C,
                             int M, int N, int K)
{
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row >= M || col >= N) return;

    float acc = 0.0f;
    for (int k = 0; k < K; ++k)
        acc += A[row * K + k] * B[k * N + col];
    C[row * N + col] = acc;
}

// ---------------------------------------------------------------------------
//  Shared-memory tiled kernel
//
//  C is partitioned into TILE x TILE tiles; each block computes one output
//  tile. For each K-tile, the block cooperatively loads a TILE x TILE slice
//  of A and B into shared memory and performs TILE multiply-adds per thread
//  using that shared data. Global-memory traffic is cut by a factor of TILE
//  compared to the naive kernel.
//
//  Works for arbitrary M, N, K -- out-of-range loads are zero-padded.
// ---------------------------------------------------------------------------
__global__ void matmul_shared(const float* __restrict__ A,
                              const float* __restrict__ B,
                              float* __restrict__ C,
                              int M, int N, int K)
{
    __shared__ float As[TILE][TILE];
    __shared__ float Bs[TILE][TILE];

    int tx = threadIdx.x;
    int ty = threadIdx.y;
    int row = blockIdx.y * TILE + ty;
    int col = blockIdx.x * TILE + tx;

    float acc = 0.0f;
    int num_k_tiles = (K + TILE - 1) / TILE;

    for (int t = 0; t < num_k_tiles; ++t) {
        int a_col = t * TILE + tx;
        int b_row = t * TILE + ty;

        // Cooperative load with bounds checking (zero-pad out-of-range)
        As[ty][tx] = (row < M && a_col < K) ? A[row * K + a_col]   : 0.0f;
        Bs[ty][tx] = (b_row < K && col < N) ? B[b_row * N + col]   : 0.0f;

        __syncthreads();

        #pragma unroll
        for (int k = 0; k < TILE; ++k)
            acc += As[ty][k] * Bs[k][tx];

        __syncthreads();
    }

    if (row < M && col < N)
        C[row * N + col] = acc;
}

// ---------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------
void fill_random(float* data, size_t n, unsigned seed) {
    std::srand(seed);
    for (size_t i = 0; i < n; ++i)
        data[i] = static_cast<float>(std::rand() % 10);
}

void print_top_left(const float* data, int rows, int cols,
                    int k, const char* label)
{
    std::cout << label << " (top-left " << k << "x" << k << "):\n";
    int r = std::min(k, rows);
    int c = std::min(k, cols);
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j)
            std::cout << std::setw(12) << std::fixed << std::setprecision(2)
                      << data[i * cols + j] << " ";
        std::cout << "\n";
    }
    std::cout << "\n";
}

// FLOPs for C (MxN) = A (MxK) * B (KxN) is 2 * M * N * K
double gflops(int M, int N, int K, float ms) {
    double flops = 2.0 * (double)M * (double)N * (double)K;
    return flops / (ms * 1.0e6);
}

// ---------------------------------------------------------------------------
//  main
// ---------------------------------------------------------------------------
int main(int argc, char** argv) {
    // C(MxN) = A(MxK) * B(KxN)
    int M = 2048, N = 2048, K = 2048;
    if (argc >= 4) {
        M = std::atoi(argv[1]);
        N = std::atoi(argv[2]);
        K = std::atoi(argv[3]);
    } else if (argc >= 2) {
        // Single argument: assume square
        M = N = K = std::atoi(argv[1]);
    }
    if (M <= 0 || N <= 0 || K <= 0) {
        std::fprintf(stderr, "Invalid dims: M=%d N=%d K=%d\n", M, N, K);
        return 1;
    }

    std::cout << "=== CUDA MatMul ===\n"
              << "  A: " << M << " x " << K << "\n"
              << "  B: " << K << " x " << N << "\n"
              << "  C: " << M << " x " << N << "\n\n";

    size_t bytes_A = (size_t)M * K * sizeof(float);
    size_t bytes_B = (size_t)K * N * sizeof(float);
    size_t bytes_C = (size_t)M * N * sizeof(float);

    // ---------- Host buffers ----------
    float* hA        = new float[(size_t)M * K];
    float* hB        = new float[(size_t)K * N];
    float* hC_naive  = new float[(size_t)M * N];
    float* hC_shared = new float[(size_t)M * N];

    fill_random(hA, (size_t)M * K, 42);
    fill_random(hB, (size_t)K * N, 1337);

    // ---------- Device buffers ----------
    float *dA, *dB, *dC;
    CHECK_CUDA(cudaMalloc(&dA, bytes_A));
    CHECK_CUDA(cudaMalloc(&dB, bytes_B));
    CHECK_CUDA(cudaMalloc(&dC, bytes_C));

    CHECK_CUDA(cudaMemcpy(dA, hA, bytes_A, cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(dB, hB, bytes_B, cudaMemcpyHostToDevice));

    // ---------- Warm-up (first launch has extra init cost) ----------
    matmul_naive<<<dim3(1,1), dim3(1,1)>>>(dA, dB, dC, 1, 1, 1);
    CHECK_CUDA(cudaDeviceSynchronize());

    // CUDA event timer
    cudaEvent_t ev_start, ev_stop;
    CHECK_CUDA(cudaEventCreate(&ev_start));
    CHECK_CUDA(cudaEventCreate(&ev_stop));

    dim3 block(TILE, TILE);
    dim3 grid((N + TILE - 1) / TILE, (M + TILE - 1) / TILE);

    // ---------- Naive ----------
    CHECK_CUDA(cudaMemset(dC, 0, bytes_C));
    CHECK_CUDA(cudaEventRecord(ev_start));
    matmul_naive<<<grid, block>>>(dA, dB, dC, M, N, K);
    CHECK_CUDA(cudaEventRecord(ev_stop));
    CHECK_CUDA(cudaEventSynchronize(ev_stop));
    CHECK_CUDA(cudaGetLastError());

    float t_naive = 0.0f;
    CHECK_CUDA(cudaEventElapsedTime(&t_naive, ev_start, ev_stop));
    CHECK_CUDA(cudaMemcpy(hC_naive, dC, bytes_C, cudaMemcpyDeviceToHost));

    std::cout << "[Naive]  " << std::fixed << std::setprecision(3)
              << t_naive << " ms  |  "
              << std::setprecision(2) << gflops(M, N, K, t_naive)
              << " GFLOPS\n";

    // ---------- Shared ----------
    CHECK_CUDA(cudaMemset(dC, 0, bytes_C));
    CHECK_CUDA(cudaEventRecord(ev_start));
    matmul_shared<<<grid, block>>>(dA, dB, dC, M, N, K);
    CHECK_CUDA(cudaEventRecord(ev_stop));
    CHECK_CUDA(cudaEventSynchronize(ev_stop));
    CHECK_CUDA(cudaGetLastError());

    float t_shared = 0.0f;
    CHECK_CUDA(cudaEventElapsedTime(&t_shared, ev_start, ev_stop));
    CHECK_CUDA(cudaMemcpy(hC_shared, dC, bytes_C, cudaMemcpyDeviceToHost));

    std::cout << "[Shared] " << std::fixed << std::setprecision(3)
              << t_shared << " ms  |  "
              << std::setprecision(2) << gflops(M, N, K, t_shared)
              << " GFLOPS\n";

    std::cout << "\nSpeedup (naive -> shared): "
              << std::setprecision(2) << (t_naive / t_shared) << "x\n\n";

    // ---------- Print top-left corners ----------
    print_top_left(hC_naive,  M, N, 4, "Naive  result");
    print_top_left(hC_shared, M, N, 4, "Shared result");

    // ---------- Verify ----------
    // Float accumulation order differs between kernels, so bit-identical
    // results are not expected. Use relative tolerance.
    const float rtol = 1e-4f;
    long mismatches = 0;
    float max_abs_err = 0.0f, max_rel_err = 0.0f;
    size_t total = (size_t)M * N;
    for (size_t i = 0; i < total; ++i) {
        float a = hC_naive[i];
        float b = hC_shared[i];
        float abs_err = std::fabs(a - b);
        float rel_err = abs_err / (std::fabs(a) + 1e-20f);
        if (abs_err > max_abs_err) max_abs_err = abs_err;
        if (rel_err > max_rel_err) max_rel_err = rel_err;
        if (rel_err > rtol) ++mismatches;
    }

    std::cout << "Verification: max_abs_err = " << std::scientific
              << std::setprecision(3) << max_abs_err
              << ", max_rel_err = " << max_rel_err << "\n";
    if (mismatches == 0)
        std::cout << "PASS: naive and shared agree within rtol="
                  << rtol << "\n";
    else
        std::cout << "FAIL: " << mismatches << " elements exceed rtol="
                  << rtol << "\n";

    // ---------- Cleanup ----------
    CHECK_CUDA(cudaEventDestroy(ev_start));
    CHECK_CUDA(cudaEventDestroy(ev_stop));
    CHECK_CUDA(cudaFree(dA));
    CHECK_CUDA(cudaFree(dB));
    CHECK_CUDA(cudaFree(dC));
    delete[] hA;
    delete[] hB;
    delete[] hC_naive;
    delete[] hC_shared;

    CHECK_CUDA(cudaDeviceReset());
    return 0;
}
