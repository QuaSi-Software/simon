#!/bin/bash
julia -e 'using Pkg; Pkg.activate("."); Pkg.add(["Dates", "Printf", "JSON", "Plots", "UUIDs"]);'
julia --threads=$SIM_NR_THREADS --project=. ./scanner.jl &
flask run --port 5000 &
wait