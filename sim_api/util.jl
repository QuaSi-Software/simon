using UUIDs
using JSON

function update_file_index(working_dir, filename)
    file_index_path = joinpath(working_dir, "file_index.json")
    alias = string(UUIDs.uuid4()) # lowercase is important to differentiate constructor from conversion

    try
        file_index = JSON.parsefile(file_index_path)
        file_index["forward"][filename] = alias
        file_index["reverse"][alias] = filename
        open(file_index_path, "w") do f
            JSON.print(f, file_index, 4)
        end
    catch e
        println("Error: Could not parse file index JSON: $e")
    end

    return alias
end