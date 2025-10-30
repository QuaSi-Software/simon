#!/bin/bash
# when you checkout this file on windows, make sure to convert from CRLF to LF because
# otherwise the script will not work inside the docker container

# because docker containers are headless, julia package Makie will not compile, complaining
# about a missing display. this issue is solved by using a virtual display provided by
# apt package xvfb
DISPLAY=:0 xvfb-run -s '-screen 0 1024x768x24' julia --threads=$SIM_NR_THREADS -e 'using Pkg; Pkg.activate("."); Pkg.develop(Pkg.PackageSpec(; path="./resie/")); Pkg.add(["Dates", "JSON", "Printf", "UUIDs", "Logging"]); Pkg.precompile();'
DISPLAY=:0 xvfb-run -s '-screen 0 1024x768x24' julia --threads=$SIM_NR_THREADS --project=. ./scanner.jl &
flask run --port 5000 &
wait