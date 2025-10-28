#!/bin/bash
# when you checkout this file on windows, make sure to convert from CRLF to LF because
# otherwise the script will not work inside the docker container
julia -e 'using Pkg; Pkg.activate("."); Pkg.add(["Dates", "Printf", "JSON", "Plots", "UUIDs"]);'
julia --threads=$SIM_NR_THREADS --project=. ./scanner.jl &
flask run --port 5000 &
wait