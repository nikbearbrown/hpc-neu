#ifndef LIFE_COMMON_HPP
#define LIFE_COMMON_HPP

#include <vector>
#include <string>
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <random>
#include <stdexcept>
#include <algorithm>

// ---------------------------------------------------------------------------
//  Grid representation
//  - Row-major 1D vector with ghost-cell border (1 cell on each side)
//  - Logical size: rows x cols
//  - Allocated size: (rows+2) x (cols+2)
// ---------------------------------------------------------------------------

struct Grid {
    int rows;          // logical rows (no ghost cells)
    int cols;          // logical cols (no ghost cells)
    int alloc_rows;    // rows + 2
    int alloc_cols;    // cols + 2
    std::vector<int> data;

    Grid() : rows(0), cols(0), alloc_rows(0), alloc_cols(0) {}

    Grid(int r, int c)
        : rows(r), cols(c),
          alloc_rows(r + 2), alloc_cols(c + 2),
          data((r + 2) * (c + 2), 0) {}

    // Access with ghost-cell offset: (i,j) in [0,rows) x [0,cols)
    inline int& operator()(int i, int j) {
        return data[(i + 1) * alloc_cols + (j + 1)];
    }
    inline int operator()(int i, int j) const {
        return data[(i + 1) * alloc_cols + (j + 1)];
    }

    // Raw access including ghost cells: ri in [0, alloc_rows), ci in [0, alloc_cols)
    inline int& raw(int ri, int ci) {
        return data[ri * alloc_cols + ci];
    }
    inline int raw(int ri, int ci) const {
        return data[ri * alloc_cols + ci];
    }

    void clear() {
        std::fill(data.begin(), data.end(), 0);
    }
};

// ---------------------------------------------------------------------------
//  Neighbor count (uses ghost cells, so no boundary checks needed)
// ---------------------------------------------------------------------------

inline int count_neighbors(const Grid& g, int i, int j) {
    // (i,j) are logical coords; shift to raw coords
    int ri = i + 1;
    int ci = j + 1;
    int w = g.alloc_cols;
    const int* d = g.data.data();
    int base = ri * w + ci;
    return d[base - w - 1] + d[base - w] + d[base - w + 1]
         + d[base     - 1]                + d[base     + 1]
         + d[base + w - 1] + d[base + w] + d[base + w + 1];
}

// ---------------------------------------------------------------------------
//  Periodic boundary: copy edges into ghost cells
// ---------------------------------------------------------------------------

inline void apply_periodic_bc(Grid& g) {
    int r = g.rows;
    int c = g.cols;
    // Top and bottom ghost rows
    for (int j = 0; j < c; ++j) {
        g.raw(0,     j + 1) = g(r - 1, j);   // top ghost = last logical row
        g.raw(r + 1, j + 1) = g(0,     j);   // bottom ghost = first logical row
    }
    // Left and right ghost columns (including corners)
    for (int ri = 0; ri < g.alloc_rows; ++ri) {
        g.raw(ri, 0)     = g.raw(ri, c);      // left ghost = rightmost logical col
        g.raw(ri, c + 1) = g.raw(ri, 1);      // right ghost = leftmost logical col
    }
}

// ---------------------------------------------------------------------------
//  Initialization patterns
// ---------------------------------------------------------------------------

enum class Pattern { RANDOM, GLIDER, ACORN, R_PENTOMINO };

inline Pattern parse_pattern(const std::string& s) {
    if (s == "glider")     return Pattern::GLIDER;
    if (s == "acorn")      return Pattern::ACORN;
    if (s == "rpentomino") return Pattern::R_PENTOMINO;
    return Pattern::RANDOM;
}

inline void init_grid(Grid& g, Pattern pat, double density = 0.3, unsigned seed = 42) {
    g.clear();
    int mr = g.rows / 2;
    int mc = g.cols / 2;

    switch (pat) {
    case Pattern::GLIDER:
        // Classic glider near center
        g(mr - 1, mc    ) = 1;
        g(mr,     mc + 1) = 1;
        g(mr + 1, mc - 1) = 1;
        g(mr + 1, mc    ) = 1;
        g(mr + 1, mc + 1) = 1;
        break;

    case Pattern::ACORN:
        // Acorn: takes 5206 generations to stabilize
        g(mr, mc - 3) = 1;
        g(mr, mc - 1) = 1;
        g(mr - 1, mc - 1) = 1; // shifted up-left
        g(mr - 1, mc - 2) = 1;
        g(mr,     mc    ) = 1;
        g(mr + 1, mc - 3) = 1;
        g(mr + 1, mc - 2) = 1;
        g(mr + 1, mc + 1) = 1;
        g(mr + 1, mc + 2) = 1;
        g(mr + 1, mc + 3) = 1;
        break;

    case Pattern::R_PENTOMINO:
        // R-pentomino
        g(mr - 1, mc    ) = 1;
        g(mr - 1, mc + 1) = 1;
        g(mr,     mc - 1) = 1;
        g(mr,     mc    ) = 1;
        g(mr + 1, mc    ) = 1;
        break;

    case Pattern::RANDOM:
    default:
        std::mt19937 rng(seed);
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        for (int i = 0; i < g.rows; ++i)
            for (int j = 0; j < g.cols; ++j)
                g(i, j) = (dist(rng) < density) ? 1 : 0;
        break;
    }
    apply_periodic_bc(g);
}

// ---------------------------------------------------------------------------
//  Distributed initialization: each rank fills only its local strip
//  global_row_offset: the global row index of this rank's first local row
//  global_rows/global_cols: full grid dimensions (for pattern placement)
// ---------------------------------------------------------------------------

inline void init_grid_local(Grid& g, Pattern pat, int global_rows, int global_cols,
                            int global_row_offset,
                            double density = 0.3, unsigned seed = 42) {
    g.clear();
    int mr = global_rows / 2;   // global center row
    int mc = global_cols / 2;   // global center col

    // Helper: set cell at global (gr, gc) if it falls within this rank's strip
    auto set_if_local = [&](int gr, int gc) {
        int local_i = gr - global_row_offset;
        if (local_i >= 0 && local_i < g.rows && gc >= 0 && gc < g.cols)
            g(local_i, gc) = 1;
    };

    switch (pat) {
    case Pattern::GLIDER:
        set_if_local(mr - 1, mc    );
        set_if_local(mr,     mc + 1);
        set_if_local(mr + 1, mc - 1);
        set_if_local(mr + 1, mc    );
        set_if_local(mr + 1, mc + 1);
        break;

    case Pattern::ACORN:
        set_if_local(mr - 1, mc - 2);
        set_if_local(mr,     mc    );
        set_if_local(mr + 1, mc - 3);
        set_if_local(mr + 1, mc - 2);
        set_if_local(mr + 1, mc + 1);
        set_if_local(mr + 1, mc + 2);
        set_if_local(mr + 1, mc + 3);
        break;

    case Pattern::R_PENTOMINO:
        set_if_local(mr - 1, mc    );
        set_if_local(mr - 1, mc + 1);
        set_if_local(mr,     mc - 1);
        set_if_local(mr,     mc    );
        set_if_local(mr + 1, mc    );
        break;

    case Pattern::RANDOM:
    default:
        // Advance RNG to this rank's starting position so results
        // match the serial version cell-for-cell
        std::mt19937 rng(seed);
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        // Skip rows before this rank's strip
        for (int i = 0; i < global_row_offset; ++i)
            for (int j = 0; j < global_cols; ++j)
                dist(rng);  // discard
        // Fill this rank's rows
        for (int i = 0; i < g.rows; ++i)
            for (int j = 0; j < g.cols; ++j)
                g(i, j) = (dist(rng) < density) ? 1 : 0;
        break;
    }
}

// ---------------------------------------------------------------------------
//  ASCII display (small grids only)
// ---------------------------------------------------------------------------

inline void print_grid(const Grid& g, int generation, std::ostream& out = std::cout) {
    out << "Generation " << generation << "  (" << g.rows << "x" << g.cols << ")\n";
    for (int i = 0; i < g.rows; ++i) {
        for (int j = 0; j < g.cols; ++j)
            out << (g(i, j) ? '#' : '.');
        out << '\n';
    }
    out << '\n';
}

// ---------------------------------------------------------------------------
//  Count live cells
// ---------------------------------------------------------------------------

inline long count_alive(const Grid& g) {
    long n = 0;
    for (int i = 0; i < g.rows; ++i)
        for (int j = 0; j < g.cols; ++j)
            n += g(i, j);
    return n;
}

// ---------------------------------------------------------------------------
//  Simple wall-clock timer
// ---------------------------------------------------------------------------

class Timer {
    using Clock = std::chrono::high_resolution_clock;
    Clock::time_point t0;
public:
    Timer() : t0(Clock::now()) {}
    void reset() { t0 = Clock::now(); }
    double elapsed_ms() const {
        return std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
    }
    double elapsed_sec() const {
        return std::chrono::duration<double>(Clock::now() - t0).count();
    }
};

// ---------------------------------------------------------------------------
//  Command-line argument helper
// ---------------------------------------------------------------------------

struct SimConfig {
    int rows        = 100;
    int cols        = 100;
    int generations = 100;
    Pattern pattern = Pattern::RANDOM;
    double density  = 0.3;
    unsigned seed   = 42;
    bool display    = false;   // print each generation (only useful for small grids)
    int display_freq = 1;      // print every N generations when display=true

    void parse(int argc, char** argv) {
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--rows"    && i + 1 < argc) rows        = std::atoi(argv[++i]);
            else if (arg == "--cols"    && i + 1 < argc) cols        = std::atoi(argv[++i]);
            else if (arg == "--gens"    && i + 1 < argc) generations = std::atoi(argv[++i]);
            else if (arg == "--pattern" && i + 1 < argc) pattern     = parse_pattern(argv[++i]);
            else if (arg == "--density" && i + 1 < argc) density     = std::atof(argv[++i]);
            else if (arg == "--seed"    && i + 1 < argc) seed        = (unsigned)std::atoi(argv[++i]);
            else if (arg == "--display") display = true;
            else if (arg == "--display-freq" && i + 1 < argc) display_freq = std::atoi(argv[++i]);
            else if (arg == "--help") {
                std::cout << "Usage: " << argv[0] << " [options]\n"
                    << "  --rows N        Grid rows (default: 100)\n"
                    << "  --cols N        Grid cols (default: 100)\n"
                    << "  --gens N        Number of generations (default: 100)\n"
                    << "  --pattern P     Pattern: random|glider|acorn|rpentomino (default: random)\n"
                    << "  --density D     Random fill density 0.0-1.0 (default: 0.3)\n"
                    << "  --seed S        RNG seed (default: 42)\n"
                    << "  --display       Print grid each generation\n"
                    << "  --display-freq N  Print every N-th generation (default: 1)\n"
                    << "  --help          Show this message\n";
                std::exit(0);
            }
        }
    }
};

#endif
