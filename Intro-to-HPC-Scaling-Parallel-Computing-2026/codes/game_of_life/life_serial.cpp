// ===========================================================================
//  Conway's Game of Life -- Serial Implementation
// ===========================================================================

#include "life_common.hpp"

// One simulation step: read from 'src', write to 'dst'
void step(const Grid& src, Grid& dst) {
    for (int i = 0; i < src.rows; ++i) {
        for (int j = 0; j < src.cols; ++j) {
            int n = count_neighbors(src, i, j);
            int alive = src(i, j);
            // Birth: dead cell with exactly 3 neighbors becomes alive
            // Survival: live cell with 2 or 3 neighbors stays alive
            // Death: everything else
            dst(i, j) = (n == 3) || (alive && n == 2) ? 1 : 0;
        }
    }
    apply_periodic_bc(dst);
}

int main(int argc, char** argv) {
    SimConfig cfg;
    cfg.parse(argc, argv);

    Grid current(cfg.rows, cfg.cols);
    Grid next(cfg.rows, cfg.cols);
    init_grid(current, cfg.pattern, cfg.density, cfg.seed);

    std::cout << "[Serial] Grid: " << cfg.rows << "x" << cfg.cols
              << " | Generations: " << cfg.generations << "\n";

    if (cfg.display)
        print_grid(current, 0);

    Timer timer;

    for (int gen = 1; gen <= cfg.generations; ++gen) {
        step(current, next);
        std::swap(current, next);

        if (cfg.display && (gen % cfg.display_freq == 0))
            print_grid(current, gen);
    }

    double elapsed = timer.elapsed_sec();
    long alive = count_alive(current);

    std::cout << "[Serial] Completed in " << elapsed << " s\n";
    std::cout << "[Serial] Live cells at generation " << cfg.generations
              << ": " << alive << "\n";
    std::cout << "[Serial] Throughput: "
              << (double)cfg.rows * cfg.cols * cfg.generations / elapsed / 1e6
              << " Mcells/s\n";

    return 0;
}
