#!/usr/bin/env bash
set -e

# settings
repetitions=15
threads=(1 2 4 8 16 32 64)
chunks=(4 16 64 256 512)
batches=(4 16 64 256 512)

make
mkdir -p results
export OMP_DYNAMIC=FALSE # Prevent OpenMP from changing the requested number of threads

# Run a program and save its timings on csv file
run() {
    local file=$1 columns=$2
    shift 2
    echo "Running: $*"

    local output seconds
    output=$("$@")
    seconds=$(awk '/^Total runtime/ {print $NF; exit}' <<< "$output")

    printf '%s,%s\n' "$columns" "$seconds" >> "$file"
}

# CSV headers
echo 'repeat,total_seconds' > results/sequential.csv
echo 'version,threads,repeat,total_seconds' > results/static.csv
echo 'version,threads,chunk,repeat,total_seconds' > results/dynamic.csv
echo 'version,threads,batch,repeat,total_seconds' > results/pipeline.csv

# All performance benchmarks
for ((r = 1; r <= repetitions; r++)); do
    echo "Starting repetition $r/$repetitions"
    run results/sequential.csv "$r" ./bin/sequential

    for p in "${threads[@]}"; do
        run results/static.csv "openmp,$p,$r" ./bin/openmp-static-dynamic static "$p"
        run results/static.csv "std-thread,$p,$r" ./bin/std-thread-static "$p"

        for c in "${chunks[@]}"; do
            run results/dynamic.csv "openmp,$p,$c,$r" ./bin/openmp-static-dynamic dynamic "$p" "$c"
            run results/dynamic.csv "std-thread,$p,$c,$r" ./bin/std-thread-dynamic "$p" "$c"
        done

        for b in "${batches[@]}"; do
            run results/pipeline.csv "openmp,$p,$b,$r" ./bin/openmp-pipeline "$p" "$b"
            run results/pipeline.csv "std-thread,$p,$b,$r" ./bin/std-thread-pipeline "$p" "$b"

        done
    done
done

echo "CSV files written to results/"
