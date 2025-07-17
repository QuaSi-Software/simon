using Base.Threads
using Printf
using Dates

function process_subdirectory(dir_path::String)
    @info "[$(Dates.now())] Started processing: $(dir_path) on thread #$(Threads.threadid())"
    sleep(10) # Simulate work
    set_status(dir_path, "finished")
    @info "[$(Dates.now())] Finished processing: $(dir_path)"
end

function set_status(dir_path::String, status::String)
    status_path = joinpath(dir_path, "status")
    open(status_path, "w") do file
        write(file, "$status\n")
        write(file, "$(Dates.now())")
    end
end

function get_status(dir_path::String)
    status = "unknown"
    status_path = joinpath(dir_path, "status")
    if isfile(status_path)
        open(status_path, "r") do file
            for line in readlines(file)
                status = lowercase(strip(line))
                break
            end
        end
    end
    return status
end

function scan_loop()
    @info "Starting scanner with $(Threads.nthreads()) threads and on #$(Threads.threadid())"
    while true
        try
            for dir_path in readdir("./runs", join=true)
                if isdir(dir_path)
                    if get_status(dir_path) == "waiting"
                        set_status(dir_path, "running")
                        Threads.@spawn process_subdirectory(dir_path)
                    end
                end
            end
        catch e
            @warn "Error during scanning: $e"
        end
        sleep(1)
    end
end

scan_loop()
