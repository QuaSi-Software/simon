using JSON

include("./resie/src/resie_logger.jl")
using .Resie_Logger

using Resie

include("util.jl")

function simulate(working_dir)
    config_file = joinpath(working_dir, "aliased_config.json")
    if !isfile(config_file)
        println("Error: Could not find config file '$config_file'")
        return
    end

    println("dummy")
    run = Resie.SimulationRun(parameters::Dict{String,Any}(), Dict{String,Any}(), Vector{Any}())
    println(run)

    println("Success: Simulation complete")
end
