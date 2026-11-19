all: bin/sequential bin/openmp-static-dynamic bin/openmp-pipeline bin/std-thread-static bin/std-thread-dynamic bin/std-thread-pipeline

bin:
	mkdir -p bin

bin/sequential: sequential.cpp lhs_generator.cpp simulation-utils.hpp | bin
	g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic sequential.cpp lhs_generator.cpp -o bin/sequential

bin/openmp-static-dynamic: openmp-static-dynamic.cpp lhs_generator.cpp simulation-utils.hpp | bin
	g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -fopenmp openmp-static-dynamic.cpp lhs_generator.cpp -o bin/openmp-static-dynamic

bin/openmp-pipeline: openmp-pipeline.cpp simulation-utils.hpp | bin
	g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -fopenmp openmp-pipeline.cpp -o bin/openmp-pipeline

bin/std-thread-static: std-thread-static.cpp lhs_generator.cpp simulation-utils.hpp | bin
	g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -pthread std-thread-static.cpp lhs_generator.cpp -o bin/std-thread-static

bin/std-thread-dynamic: std-thread-dynamic.cpp lhs_generator.cpp simulation-utils.hpp | bin
	g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -pthread std-thread-dynamic.cpp lhs_generator.cpp -o bin/std-thread-dynamic

bin/std-thread-pipeline: std-thread-pipeline.cpp simulation-utils.hpp | bin
	g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -pthread std-thread-pipeline.cpp -o bin/std-thread-pipeline

clean:
	rm -rf bin

.PHONY: all clean
