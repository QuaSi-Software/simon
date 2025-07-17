#!/bin/bash
julia -e 'using Pkg; Pkg.activate("."); Pkg.add(["Dates", "Printf", "JSON"]);'
julia --threads=$SIM_NR_THREADS ./scanner.jl &
flask run --port 5000 &
wait