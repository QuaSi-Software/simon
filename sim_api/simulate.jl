using JSON
using Plots

function julia_set(sx, sy, nx, ny, c=-0.744 + 0.148im)::Array{UInt8, 2}
	iterations_till_divergence = Array{UInt8, 2}(undef, nx, ny)
    step_x = sx / nx
    step_y = sy / ny
    for ix in range(1, length=nx)
		for iy in range(1, length=ny)
			iterations_till_divergence[ix,iy] = trunc(UInt8, 0)
			z = ix * step_x - sx * 0.5 + (iy * step_y - sy * 0.5)*1im
			for i in 0:254
				z = z^2 + c
				if abs(z) > 4.0
					iterations_till_divergence[ix,iy] = trunc(UInt8, i)
					break
                end
            end
        end
    end

	return iterations_till_divergence
end

function plot_julia_set(sx, sy, values::Array{UInt8, 2}, working_dir::String)
    nx, ny = size(values)
    x_min, x_max = -sx/2, sx/2
    y_min, y_max = -sy/2, sy/2
    heatmap(
        range(x_min, x_max; length=nx),
        range(y_min, y_max; length=ny),
        values',
        color=:viridis,
        aspect_ratio=:equal,
        title="Julia Set",
        xlabel="Re",
        ylabel="Im",
        dpi=1000
    )
    savefig(joinpath(working_dir, "julia_set.png"))
end

function simulate(working_dir)
    config_file = joinpath(working_dir, "aliased_config.json")
    if !isfile(config_file)
        println("Error: Could not find config file '$config_file'")
        return
    end

    try
        config = JSON.parsefile(config_file)
        c = Float64(config["c_re"]) + Float64(config["c_im"]) * 1im
        plot_julia_set(3.0, 2.0, julia_set(3.0, 2.0, 5000, 5000, c), working_dir)
    catch e
        println("Error: Could not parse JSON in config file: $e")
        return
    end

    println("Success: Simulation complete")
end
