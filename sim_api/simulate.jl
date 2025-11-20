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

    log_to_console = false
    log_to_file = true
    general_logfile_path = joinpath(working_dir, "./logfile_general.log")
    balanceWarn_logfile_path = joinpath(working_dir, "./logfile_balanceWarn.log")
    min_log_level = Resie_Logger.Logging.Info
    log_file_general, log_file_balanceWarn = Resie_Logger.start_logger(log_to_console,
                                                                       log_to_file,
                                                                       general_logfile_path,
                                                                       balanceWarn_logfile_path,
                                                                       min_log_level,
                                                                       config_file)

    run_ID = uuid1() # should we rather use the sim API run ID?
    try
        Resie.load_and_run(config_file, run_ID)
    catch exc
        io = IOBuffer()
        showerror(io, exc)
        print(io, stacktrace(catch_backtrace()))
        msg = String(take!(io))
        @error msg
    finally
        Resie.close_run(run_ID)
        Resie_Logger.close_logger(log_file_general, log_file_balanceWarn)
    end
end
