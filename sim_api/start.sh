#!/bin/bash
julia -e 'using Pkg; Pkg.activate("."); Pkg.add(["Dates", "Printf", "JSON"]);'
julia ./scanner.jl &
flask run --port 5000 &
wait