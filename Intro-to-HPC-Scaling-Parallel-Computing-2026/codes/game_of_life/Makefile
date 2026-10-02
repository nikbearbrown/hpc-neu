# ===========================================================================
#  Makefile for Conway's Game of Life
#  Targets: serial, openmp, all, clean
# ===========================================================================

CXX       = g++

CXXFLAGS  = -O2 -std=c++17
OMP_FLAGS = -fopenmp

# Targets
SERIAL    = life_serial
OPENMP    = life_openmp

.PHONY: all serial openmp clean help

all: serial openmp

serial: $(SERIAL)
openmp: $(OPENMP)

$(SERIAL): life_serial.cpp life_common.hpp
	$(CXX) $(CXXFLAGS) -o $@ $<

$(OPENMP): life_openmp.cpp life_common.hpp
	$(CXX) $(CXXFLAGS) $(OMP_FLAGS) -o $@ $<

clean:
	rm -f $(SERIAL) $(OPENMP) $(MPI_OMP)

# ---------------------------------------------------------------------------
#  Quick-run targets for testing / demo
# ---------------------------------------------------------------------------

run_serial: $(SERIAL)
	./$(SERIAL) --rows 1000 --cols 1000 --gens 100

run_openmp: $(OPENMP)
	OMP_NUM_THREADS=4 ./$(OPENMP) --rows 1000 --cols 1000 --gens 100

# Small grid with display for visual demo
demo: $(SERIAL)
	./$(SERIAL) --rows 20 --cols 40 --gens 20 --pattern glider --display

help:
	@echo "Targets:"
	@echo "  all         Build all versions"
	@echo "  serial      Build serial version"
	@echo "  openmp      Build OpenMP version"
	@echo "  run_serial  Build and run serial (1000x1000, 100 gens)"
	@echo "  run_openmp  Build and run OpenMP (4 threads)"
	@echo "  demo        Small visual demo with glider"
	@echo "  clean       Remove binaries"
