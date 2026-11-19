#include "simulation-utils.hpp"
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <mutex>
#include <random>
#include <string>
#include <thread>
#include <utility>
#include <vector>

struct Batch {
    std::vector<std::vector<double>> configurations;
    SimulationCounters results{};
};

struct Parameter {
    std::string name;
    double min;
    double max;
};

int main(int argc, char* argv[]) {

    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " NUM_THREADS BATCH_SIZE\n";
        return 1;
    }

    const int numThreads = std::atoi(argv[1]);
    const int batchSize = std::atoi(argv[2]);

    auto startTotal = std::chrono::steady_clock::now();

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
    const double initialTumor = 1e6;
    SimulationCounters globalResults{};

    // Matrix of interval indices for each parameter
    std::vector<std::vector<std::size_t>> intervalMatrix(numParameters, std::vector<std::size_t>(N));
    // Initialize and shuffle interval indices in the intervalMatrix
    for (std::size_t j = 0; j < numParameters; ++j) {
        for (std::size_t i = 0; i < N; ++i) {
            intervalMatrix[j][i] = i + 1;
        }
        std::shuffle(intervalMatrix[j].begin(), intervalMatrix[j].end(), rng);
    }

    // Generate LHS configurations in batches
    const std::size_t batchCount = N / batchSize + (N % batchSize != 0);
    std::vector<Batch> batches(batchCount);

    // Simulation for a batch of configurations
    auto processBatch = [&](std::size_t b) {
        auto& batch = batches[b];

        for (const auto& configuration : batch.configurations) {
            // Initialize N, M and T cell populations
            double N = initialTumor * (1.0 - configuration[R_LA]);
            double M = initialTumor * configuration[R_LA];
            double T = initialTumor * configuration[R_IT];
            const State initialState = {N, M, T};

            const SimulationResult result = simulate150Days(initialState, configuration);

            recordResult(batch.results, result);
        }
    };

    // Shared queue and synchronization variables
    std::deque<std::size_t> batchIndexQueue;
    std::mutex queueMutex;
    std::condition_variable queueCV;
    bool producerFinished = false;

    // Consumer function: take and process ready batches
    auto consumer = [&]() {
        while (true) {
            std::size_t b;
            {
                std::unique_lock<std::mutex> lock(queueMutex);
                queueCV.wait(lock, [&]() {return !batchIndexQueue.empty() || producerFinished;});

                if (batchIndexQueue.empty()) return;
                b = batchIndexQueue.front();
                batchIndexQueue.pop_front();
            }
            processBatch(b);
        }
    };

    // Create and start worker threads
    std::vector<std::thread> workers;
    for (int tid = 1; tid < numThreads; ++tid) {
        workers.push_back(std::thread(consumer));
    }

    // Stage 1: produce a batch of LHS configurations
    for (std::size_t b = 0; b < batchCount; ++b) {
        const std::size_t begin = b * batchSize;
        const std::size_t end = std::min(begin + batchSize, N);

        for (std::size_t i = begin; i < end; ++i) {
            std::vector<double> row(numParameters);
            for (std::size_t j = 0; j < numParameters; ++j) {
                double width = (parameters[j].max - parameters[j].min) / N;
                double intervalIndex = intervalMatrix[j][i];
                double randomOffset = uniform01(rng);
                row[j] = parameters[j].min + (intervalIndex - randomOffset) * width;
            }
            batches[b].configurations.push_back(std::move(row));
        }

        // Add the completed batch to the queue
        {
            std::lock_guard<std::mutex> lock(queueMutex);
            batchIndexQueue.push_back(b);
        }
        queueCV.notify_one();
    }

    // Signal end of production
    {
        std::lock_guard<std::mutex> lock(queueMutex);
        producerFinished = true;
    }
    queueCV.notify_all();

    // Main thread also processes remaining batches
    consumer();
    for (std::thread& t : workers) t.join();

    for (const auto& batch : batches) {
        mergeCounters(globalResults, batch.results);
    }

    auto finish = std::chrono::steady_clock::now();
    const double timeTotal = std::chrono::duration<double>(finish - startTotal).count();


    // Simulation summary and total runtime
    std::cout << "Configurations simulated: " << N << '\n'
              << "Elimination: " << globalResults.eliminated << '\n'
              << "Dormancy: " << globalResults.dormant << '\n'
              << "Escape: " << globalResults.escaped << '\n'
              << "NumericalFailure: " << globalResults.failed << '\n'
              << "Rejected steps: " << globalResults.totalRejected << '\n'
              
              << "Total runtime (s): " << timeTotal << '\n';

    std::cout << "Total threads: " << numThreads << '\n'
              << "Pipeline batch size: " << batchSize << '\n';
    return 0;
}
