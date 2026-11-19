#include "simulation-utils.hpp"
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <omp.h>
#include <string>
#include <vector>

int main(int argc, char* argv[]) {

    if (argc < 3 || argc > 4) {
        std::cerr << "Usage: " << argv[0] << " static NUM_THREADS\n"
                  << "  or: " << argv[0] << " dynamic NUM_THREADS [CHUNK]\n";
        return 1;
    }

    const std::string mode = argv[1];
    const int numThreads = std::atoi(argv[2]);
    const int chunkSize = (argc == 4) ? std::atoi(argv[3]) : 64;

    // Set OpenMP scheduling policy
    if (mode == "static") {
        omp_set_schedule(omp_sched_static, 0);
    } else {
        omp_set_schedule(omp_sched_dynamic, chunkSize);
    }

    auto startTotal = std::chrono::steady_clock::now();

    const auto configurations = LHS_generator();
    
    const std::size_t count = configurations.size();
    const double initialTumor = 1e6;
    std::size_t eliminated = 0;
    std::size_t dormant = 0;
    std::size_t escaped = 0;
    std::size_t failed = 0;
    std::size_t totalRejected = 0;

    #pragma omp parallel for schedule(runtime) num_threads(numThreads) reduction(+:eliminated,dormant,escaped,failed,totalRejected)
    for (std::size_t i = 0; i < count; ++i) {
        const std::vector<double>& configuration = configurations[i];

        // Initialize N, M and T cell populations
        double N = initialTumor * (1.0 - configuration[R_LA]);
        double M = initialTumor * configuration[R_LA];
        double T = initialTumor * configuration[R_IT];
        const State initialState = {N, M, T};


        const SimulationResult result = simulate150Days(initialState, configuration);

        if (result.outcome == Elimination) {
            ++eliminated;
        } else if (result.outcome == Dormancy) {
            ++dormant;
        } else if (result.outcome == Escape) {
            ++escaped;
        } else {
            ++failed;
        }

        totalRejected += result.rejected;
    }

    auto finish = std::chrono::steady_clock::now();
    const double totalSeconds = std::chrono::duration<double>(finish - startTotal).count();

    std::cout << "Configurations simulated: " << count << '\n'
                << "Elimination: " << eliminated << '\n'
                << "Dormancy: " << dormant << '\n'
                << "Escape: " << escaped << '\n'
                << "NumericalFailure: " << failed << '\n'
                << "Rejected steps: " << totalRejected << '\n'
                
                << "Total runtime (s): " << totalSeconds << '\n';

    std::cout << "Scheduling: " << mode << '\n'
              << "OpenMP threads: " << numThreads << '\n';
    if (mode == "dynamic")
        std::cout << "Dynamic chunk: " << chunkSize << '\n';

    return 0;
}

