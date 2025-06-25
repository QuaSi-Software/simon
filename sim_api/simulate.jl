using JSON

function main()
    if length(ARGS) < 1
        println("Error: No config filename given")
        return
    end

    filename = ARGS[1]
    if !isfile(filename)
        println("Error: Could not find config file '$filename'")
        return
    end

    try
        json_data = JSON.parsefile(filename)
        output_filename = "output.txt"
        open(output_filename, "w") do file
            for (key, value) in json_data
                println(file, "$key: $value")
            end
        end
    catch e
        println("Error: Could not parse JSON in config file: $e")
        return
    end

    println("Success: Simulation complete")
end

main()
