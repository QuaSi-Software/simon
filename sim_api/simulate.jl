using JSON
using Logging

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

    log_to_console = false
    log_to_file = true
    general_logfile_path = joinpath(working_dir, "./logfile_general.log")
    balanceWarn_logfile_path = joinpath(working_dir, "./logfile_balanceWarn.log")
    min_log_level = Resie_Logger.Logging.Info
    logger = Resie_Logger.start_logger(log_to_console,
                                       log_to_file,
                                       general_logfile_path,
                                       balanceWarn_logfile_path,
                                       min_log_level,
                                       config_file)

    run_ID = uuid1() # should we rather use the sim API run ID?
    try
        with_logger(logger) do
            Resie.load_and_run(config_file, run_ID)
        end
    catch exc
        io = IOBuffer()
        showerror(io, exc)
        print(io, stacktrace(catch_backtrace()))
        msg = String(take!(io))
        @error msg
    finally
        Resie.close_run(run_ID)
        with_logger(logger) do
            # the close_logger makes logs itself, which is why we need to use with_logger
            # or else these messages pop up in the global logger
            Resie_Logger.close_logger(logger)
        end
    end
end
