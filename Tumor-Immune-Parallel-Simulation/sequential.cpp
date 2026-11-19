#include "simulation-utils.hpp"
#include <chrono>
#include <cstddef>
#include <iostream>
#include <vector>

int main() {
    auto startTotal = std::chrono::steady_clock::now();

    const auto configurations = LHS_generator();
    auto endLHS = std::chrono::steady_clock::now();

    const std::size_t count = configurations.size();
    const double initialTumor = 1e6;
    SimulationCounters globalResults{};

    auto start = std::chrono::steady_clock::now();

    for (std::size_t i = 0; i < count; ++i) {
        const std::vector<double>& configuration = configurations[i];

        // Initialize N, M and T cell populations
        double N = initialTumor * (1.0 - configuration[R_LA]);
        double M = initialTumor * configuration[R_LA];
        double T = initialTumor * configuration[R_IT];
        const State initialState = {N, M, T};

        const SimulationResult result = simulate150Days(initialState, configuration);

        recordResult(globalResults, result);
    }

    auto finish = std::chrono::steady_clock::now();

    const double simulationSeconds = std::chrono::duration<double>(finish - start).count();
    const double lhsSeconds = std::chrono::duration<double>(endLHS - startTotal).count();
    const double totalSeconds = std::chrono::duration<double>(finish - startTotal).count();

    std::cout << "Configurations simulated: " << count << '\n'
              << "Elimination: " << globalResults.eliminated << '\n'
              << "Dormancy: " << globalResults.dormant << '\n'
              << "Escape: " << globalResults.escaped << '\n'
              << "NumericalFailure: " << globalResults.failed << '\n'
              << "Rejected steps: " << globalResults.totalRejected << '\n'
              
              << "Simulation loop (s): " << simulationSeconds << '\n'
              << "LHS generation (s): " << lhsSeconds << '\n'
              << "Total runtime (s): " << totalSeconds << '\n';
    return 0;
}
