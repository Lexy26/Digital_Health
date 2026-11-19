#include <vector>
#include <string>
#include <random>
#include <algorithm>
#include <cstddef>

struct Parameter {
    std::string name;
    double min;
    double max;
};

// create 30 000 different configurations
std::vector<std::vector<double>> LHS_generator() {

    // LHS parameter ranges
    const std::vector<Parameter> parameters = {
        {"alpha_n", 0.05, 0.6},
        {"alpha_m", 0.05, 0.6},
        {"K", 3e9, 6e9},
        {"delta_ns", 1.0, 12.0},
        {"delta_ms", 1.0, 12.0},
        {"delta_nf", 1e-8, 1e-6},
        {"delta_mf", 1e-8, 1e-6},
        {"kappa_0", 1e6, 1e8},
        {"kappa_1", 0.01, 1.0},
        {"kappa_2", 1e6, 1e8},
        {"delta_t", 0.0, 0.5},
        {"mu", 5e3, 1.5e5},
        {"delta_n", 1e-11, 1e-9},
        {"delta_m", 1e-11, 1e-9},
        {"p1", 0.0, 1.0},
        {"p2", 0.0, 1.0},
        {"alpha_nt", 0.0, 0.5},
        {"alpha_mt", 0.0, 0.5},
        {"rho_p", 1e-12, 1e-10},
        {"rho_l", 1e-12, 2e-10},
        {"epsilon_c", 1.0, 50.0},
        {"mu_PA", 6.45, 273.0},
        {"k_TQ", 1e-10, 1e-8},
        {"R_LA", 0.0, 1.0},
        {"R_IT", 1e-6, 0.1}
    };

    const std::size_t N = 30000;
    const std::size_t numParameters = parameters.size();
    std::mt19937 rng(42);
    std::uniform_real_distribution<double> uniform01(0.0, 1.0);

    // LHS final matrix: 30000 rows x 25 parameters
    std::vector<std::vector<double>> lhs(N, std::vector<double>(numParameters));

    // Matrix of interval indices for each parameter
    std::vector<std::vector<std::size_t>> intervalMatrix(numParameters, std::vector<std::size_t>(N));
    // Initialize and shuffle interval indices in the intervalMatrix
    for (std::size_t j = 0; j < numParameters; ++j) {
        for (std::size_t i = 0; i < N; ++i) {
            intervalMatrix[j][i] = i + 1;
        }
        std::shuffle(intervalMatrix[j].begin(), intervalMatrix[j].end(), rng);
    }

    // Generate one configuration at a time
    for (std::size_t i = 0; i < N; ++i) {
        for (std::size_t j = 0; j < numParameters; ++j) {
            double width = (parameters[j].max - parameters[j].min) / N;
            double intervalIndex = intervalMatrix[j][i];
            double randomOffset = uniform01(rng);

            lhs[i][j] = parameters[j].min + (intervalIndex - randomOffset) * width;
        }
    }

    return lhs;
}
