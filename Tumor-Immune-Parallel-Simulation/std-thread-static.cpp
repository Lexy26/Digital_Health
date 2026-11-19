#include "simulation-utils.hpp"
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <thread>
#include <vector>

int main(int argc, char* argv[]) {

    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " NUM_THREADS\n";
        return 1;
    }
    const int numThreads = std::atoi(argv[1]);

    auto startTotal = std::chrono::steady_clock::now();

    const auto configurations = LHS_generator();

    const std::size_t count = configurations.size();
    const double initialTumor = 1e6;
    SimulationCounters globalResults{};

    std::vector<SimulationCounters> partialResults(numThreads); // PartialResults[i], one for each thread
    std::vector<std::thread> workers;

    // Worker function
    auto worker = [&](int tid) {
        const std::size_t begin = count * tid / numThreads;
        const std::size_t end = count * (tid + 1) / numThreads;

        SimulationCounters localResults{};

        for (std::size_t i = begin; i < end; ++i) {
            const std::vector<double>& configuration = configurations[i];

            // Initialize N, M and T cell populations
            double N = initialTumor * (1.0 - configuration[R_LA]);
            double M = initialTumor * configuration[R_LA];
            double T = initialTumor * configuration[R_IT];
            const State initialState = {N, M, T};

            const SimulationResult result = simulate150Days(initialState, configuration);

            recordResult(localResults, result);
        }

        partialResults[tid] = localResults;
    };

    // Start worker threads
    for (int tid = 0; tid < numThreads; ++tid) {
        workers.push_back(std::thread(worker, tid));
    }

    // Wait for worker threads
    for (std::thread& t : workers) t.join();

    // Combine thread counters
    for (const SimulationCounters& partial : partialResults) {
        mergeCounters(globalResults, partial);
    }

    auto finish = std::chrono::steady_clock::now();

    const double totalSeconds = std::chrono::duration<double>(finish - startTotal).count();

    std::cout << "Configurations simulated: " << count << '\n'
                << "Elimination: " << globalResults.eliminated << '\n'
                << "Dormancy: " << globalResults.dormant << '\n'
                << "Escape: " << globalResults.escaped << '\n'
                << "NumericalFailure: " << globalResults.failed << '\n'
                << "Rejected steps: " << globalResults.totalRejected << '\n'
                
                << "Total runtime (s): " << totalSeconds << '\n';

    std::cout << "std::thread workers: " << numThreads << '\n';
    return 0;
}

