#include <algorithm>
#include <cmath>
#include <cstddef>
#include <vector>

// The three cell populations
struct State {
    double N;
    double M;
    double T;
};

// 23 model parameters and 2 initial-condition ratios
enum ParamIndex : std::size_t {ALPHA_N = 0, ALPHA_M, K, DELTA_NS, DELTA_MS, DELTA_NF, DELTA_MF, KAPPA_0, KAPPA_1, KAPPA_2, DELTA_T, MU, DELTA_N, DELTA_M, P1, P2, ALPHA_NT, ALPHA_MT, RHO_P, RHO_L, EPSILON_C, MU_PA, K_TQ, R_LA, R_IT};


enum Outcome {
    Elimination,
    Dormancy,
    Escape,
    NumericalFailure
};

struct SimulationResult {
    std::size_t rejected; // Number of rejected steps
    Outcome outcome;
};

// ODE system
inline State ode_model(const State& s, const std::vector<double>& paramConfig) {
    // High-antigenicity tumor cells
    const double dN =
        // growth
        paramConfig[ALPHA_N] * s.N * (1.0 - (s.N + s.M) / paramConfig[K])
        // slow killing
        - paramConfig[DELTA_NS] * (1.0 - paramConfig[P1]) * s.N * s.T / (paramConfig[KAPPA_1] * s.T + (s.N + s.M) + paramConfig[KAPPA_0])
        // fast killing
        - paramConfig[DELTA_NF] * paramConfig[P1] * s.N * s.T;

    // Low-antigenicity tumor cells
    const double dM =
        // growth
        paramConfig[ALPHA_M] * s.M * (1.0 - (s.N + s.M) / paramConfig[K])
        // slow killing
        - paramConfig[DELTA_MS] * (1.0 - paramConfig[P2]) * s.M * s.T / (paramConfig[KAPPA_1] * s.T + (s.N + s.M) + paramConfig[KAPPA_0])
        // fast killing
        - paramConfig[DELTA_MF] * paramConfig[P2] * s.M * s.T;

    // T-cell
    const double dT =
        // recruitment
        (paramConfig[MU]
        // proliferation
        + paramConfig[ALPHA_NT] * s.N * s.T / (paramConfig[KAPPA_2] + s.N) + paramConfig[ALPHA_MT] * s.M * s.T / (paramConfig[KAPPA_2] + s.M))
        // T-cell death: N-mediated, M-mediated, and natural
        - (paramConfig[DELTA_N] * s.N * s.T + paramConfig[DELTA_M] * s.M * s.T + paramConfig[DELTA_T] * s.T);

    return {dN, dM, dT};
}

// System state update using Euler's method
inline State eulerStep(const State& s, const std::vector<double>& paramConfig, double h) {
    const State d = ode_model(s, paramConfig);
    return {
        s.N + h * d.N,
        s.M + h * d.M,
        s.T + h * d.T
    };
}

// Tumor simulation for a given parameter configuration
inline SimulationResult simulate150Days(State s, const std::vector<double>& paramConfig)
{
    const double finalDay = 150.0;
    const double eliminationThreshold = 1e5;  // 0.1 mm^3
    const double escapeThreshold = 5e8;       // 500 mm^3
    const std::size_t maxRejectedSteps = 80;

    double t = 0.0; // time
    double h = 0.01; // time step
    std::size_t rejected = 0;

    while (t < finalDay && (s.N + s.M) > eliminationThreshold) {
        if (rejected >= maxRejectedSteps) {
            return {rejected, NumericalFailure};
        }

        const double step = std::min(h, finalDay - t);
        if (!(step > 0.0) || !std::isfinite(step) || !(t + step > t)) {
            return {rejected, NumericalFailure};
        }

        const State s_tmp = eulerStep(s, paramConfig, step);

        // Reject invalid states
        if (!std::isfinite(s_tmp.N) || !std::isfinite(s_tmp.M) || !std::isfinite(s_tmp.T) || s_tmp.N < 0.0 || s_tmp.M < 0.0 || s_tmp.T < 0.0) {
            ++rejected;
            h /= 2.0;
            continue;
        }

        s = s_tmp;
        t += step;
    }

    const double tumor = s.N + s.M;
    Outcome outcome;
    if (tumor <= eliminationThreshold) {
        outcome = Elimination;
    } else if (tumor <= escapeThreshold) {
        outcome = Dormancy;
    } else {
        outcome = Escape;
    }

    return {rejected, outcome};
}

// Simulation counters
struct SimulationCounters {
    std::size_t eliminated = 0;
    std::size_t dormant = 0;
    std::size_t escaped = 0;
    std::size_t failed = 0;
    std::size_t totalRejected = 0;
};

// Update counters with a simulation result
inline void recordResult(SimulationCounters& counters, const SimulationResult& result) {
    if (result.outcome == Elimination) {
        ++counters.eliminated;
    } else if (result.outcome == Dormancy) {
        ++counters.dormant;
    } else if (result.outcome == Escape) {
        ++counters.escaped;
    } else {
        ++counters.failed;
    }
    counters.totalRejected += result.rejected;
}

// Combine simulation counters
inline void mergeCounters(SimulationCounters& total, const SimulationCounters& partial) {
    total.eliminated += partial.eliminated;
    total.dormant += partial.dormant;
    total.escaped += partial.escaped;
    total.failed += partial.failed;
    total.totalRejected += partial.totalRejected;
}

// Implemented separately in lhs_generator.cpp
std::vector<std::vector<double>> LHS_generator();
