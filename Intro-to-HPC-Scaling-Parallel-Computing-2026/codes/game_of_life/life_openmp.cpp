// ===========================================================================
//  Conway's Game of Life -- OpenMP Implementation
//
//  Key difference from serial: the nested loop in step() is parallelized
//  with an OpenMP parallel-for directive. The outer loop (rows) is split
//  across threads. No synchronization needed because each cell write is
//  independent (double-buffered grids).
// ===========================================================================

#include "life_common.hpp"
#include <omp.h>

void step_omp(const Grid& src, Grid& dst) {
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < src.rows; ++i) {
        for (int j = 0; j < src.cols; ++j) {
            int n = count_neighbors(src, i, j);
            int alive = src(i, j);
            dst(i, j) = (n == 3) || (alive && n == 2) ? 1 : 0;
        }
    }
    apply_periodic_bc(dst);
}

int main(int argc, char** argv) {
    SimConfig cfg;
    cfg.parse(argc, argv);

    int num_threads = omp_get_max_threads();

    Grid current(cfg.rows, cfg.cols);
    Grid next(cfg.rows, cfg.cols);
    init_grid(current, cfg.pattern, cfg.density, cfg.seed);

    std::cout << "[OpenMP] Grid: " << cfg.rows << "x" << cfg.cols
              << " | Generations: " << cfg.generations
              << " | Threads: " << num_threads << "\n";

    if (cfg.display)
        print_grid(current, 0);

    Timer timer;

    for (int gen = 1; gen <= cfg.generations; ++gen) {
        step_omp(current, next);
        std::swap(current, next);

        if (cfg.display && (gen % cfg.display_freq == 0))
            print_grid(current, gen);
    }

    double elapsed = timer.elapsed_sec();
    long alive = count_alive(current);

    std::cout << "[OpenMP] Completed in " << elapsed << " s\n";
    std::cout << "[OpenMP] Live cells at generation " << cfg.generations
              << ": " << alive << "\n";
    std::cout << "[OpenMP] Throughput: "
              << (double)cfg.rows * cfg.cols * cfg.generations / elapsed / 1e6
              << " Mcells/s\n";

    return 0;
}
