API_ROOT = "http://localhost:5001/"

run_status = {}

function by_id(id) {
    return document.getElementById(id)
}

function by_cl(class_name) {
    return Array.from(document.getElementsByClassName(class_name))
}

function last(array) {
    return array[array.length-1]
}

function except_first(array) {
    return array.slice(1)
}

function except_last(array) {
    return array.slice(0, -1)
}

function format_nc_file_path(file_path, selector, decode) {
    if (selector === undefined) {
        selector = "filename"
    }
    if (decode === undefined) {
        decode = true
    }

    if (file_path.startsWith("/")) {
        file_path = except_first(file_path)
    }
    if (last(file_path) === "/") {
        file_path = except_last(file_path)
    }

    let path = file_path
    let splitted = file_path.split("/")
    if (selector == "full") {
        path = file_path
    } else if (selector == "filename") {
        path = last(splitted)
    } else if (selector == "dir_path") {
        path = except_last(splitted).join("/");
    }

    return decode ? decodeURI(path) : path
}

function add_to_query_list(query_name, response, result) {
    let item = '<div class="query-result card"><div class="card-body">'
            + '<span>Request: ' + query_name + '</span><br/>'
            + '<span>Code: ' + (response.status ? response.status : 'Error') + '</span><br/>'
            + '<span>Message: ' + (result["message"] ? result["message"] : '') + '</span><br/>'
            + '<span>Error: ' + (result["error"] ? result["error"] : '') + '</span>'
            + '</div></div>'
    by_id('query-list').innerHTML = item + by_id('query-list').innerHTML
}

function clear_errors() {
    by_id("error-list").innerHTML = ""
    by_id("error-list").classList.add("hidden")
    by_id("error-label").classList.add("hidden")
}

function set_errors(message) {
    by_id("error-list").innerHTML = "<li>" + message + "</li>"
    by_id("error-list").classList.remove("hidden")
    by_id("error-label").classList.remove("hidden")
}

function add_error(message) {
    by_id("error-list").innerHTML = by_id("error-list").innerHTML + "<li>" + message + "</li>"
    by_id("error-list").classList.remove("hidden")
    by_id("error-label").classList.remove("hidden")
}

async function fetch_results(run_id) {
    let element = by_id("config-file-selection")
    let input_file_dir = element.options[element.selectedIndex].dataset.dirname
    let response = await fetch(API_ROOT + 'fetch_results/' + run_id, {
        method: 'POST',
        body: JSON.stringify({"destination_dir": input_file_dir}),
        headers: {"Content-Type": "application/json"}
    })
    let result = response.status >= 400 ? await response.json() : {}
    add_to_query_list('fetch_results', response, result)

    let blob = await response.blob();
    let img = document.createElement('img');
    img.src = URL.createObjectURL(blob);
    img.alt = 'Simulation Result';
    img.className = 'simulation-results';
    img.width = 900;
    img.height = 533;
    let results_div = by_id('simulation-results');
    results_div.innerHTML = '';
    results_div.appendChild(img);
}

async function check_status(run_id) {
    let response = await fetch(
        API_ROOT + 'run_status/' + run_id,
        {method: 'GET'}
    )
    let result = await response.json()
    add_to_query_list('run_status', response, result)

    run_status["status"] = result["code"]
    by_id('run-status').innerText = run_status["status"]

    if (run_status["status"] === "finished") {
        clearInterval(run_status["interval_id"])
        await fetch_results(run_id)
    }
}

async function switch_directory(item) {
    let new_val = item.dataset.dirname
    if (new_val == "..") {
        new_val = by_id("nc-current-dir").dataset.dirname
        let splitted = new_val.split("/")
        new_val = except_last(splitted).join("/")
    }
    by_id("nc-current-dir").setAttribute("data-dirname", new_val)
    by_id("nc-current-dir").innerText = "/" + format_nc_file_path(new_val, "filename", true)
    fetch_nc_file_list()
}

async function get_run_id() {
    let response = await fetch(
        API_ROOT + "get_run_id"
    )
    let data = await response.json()
    add_to_query_list("get_run_id", response, data)
    return data["run_id"]
}

async function upload_file(item) {
    if (run_status["run_id"] === undefined) {
        run_status["run_id"] = await get_run_id()
        by_id('run-id').innerText = run_status["run_id"]
        by_id('run-status').innerText = "new"
    }

    let response = await fetch(
        API_ROOT + "upload_file_to_sim_run/" + run_status["run_id"],
        {
            method: "POST",
            body: JSON.stringify({"file_path": item.dataset.filename}),
            headers: {
                "Content-Type": "application/json"
            }
        }
    )
    add_to_query_list("upload_file_to_sim_run", response, {})

    if (response.status < 300) {
        by_id("uploaded-files").innerHTML = by_id("uploaded-files").innerHTML +
            "<li>/" + format_nc_file_path(item.dataset.filename, "full", true) + "</li>"
        by_id("config-file-selection").innerHTML = by_id("config-file-selection").innerHTML +
            '<option value="' + format_nc_file_path(item.dataset.filename, "filename", false) + '" ' +
            'data-dirname="'  + format_nc_file_path(item.dataset.filename, "dir_path", false) + '">' +
            format_nc_file_path(item.dataset.filename, "filename", true) + "</option>"
    } else {
        let result = await response.json()
        set_errors("File upload failed :" + result["error"])
    }
}

async function fetch_nc_file_list() {
    by_id("nc-file-list-blocker").classList.remove("hidden")

    let curr_dir = by_id("nc-current-dir").dataset.dirname

    let response = await fetch(
        API_ROOT + "get_files",
        {
            method: "POST",
            body: JSON.stringify({"dir_path": curr_dir}),
            headers: {
                "Content-Type": "application/json"
            }
        }
    )
    let files = await response.json()
    add_to_query_list("get_files", response, files)

    let items = []
    files.sort((a, b) => {
        if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
        return a.name.localeCompare(b.name)
    }).forEach(item => {
        if (item.name != "/" && item.name != curr_dir) {
            let prefix = item.is_dir ? "|\>&nbsp;" : "|&nbsp;&nbsp;"
            items.push(
                "<li "
                + "class='" + (item.is_dir ? "nc-file-list-dir" : "nc-file-list-file") + "' "
                + "data-" + (item.is_dir ? "dirname" : "filename") + "='"+ item.name + "' "
                + ">"
                + prefix + format_nc_file_path(item.name, "filename", true)
                + "</li>"
            )
        }
    })

    by_id('nc-file-list-items').innerHTML = (
        '<ul class="no-bullet">'
        + '<li class="nc-file-list-dir" data-dirname="..">|\>&nbsp;..</li>'
        + items.join("\n") + "</ul>"
    )

    by_cl("nc-file-list-dir").forEach(item => {
        item.onclick = async function(event) {
            event.preventDefault()
            switch_directory(item)
        }
    })

    by_cl("nc-file-list-file").forEach(item => {
        item.onclick = async function(event) {
            event.preventDefault()
            upload_file(item)
        }
    })

    by_id("nc-file-list-blocker").classList.add("hidden")
}

async function start_simulation_from_form(form_element) {
    if (run_status["run_id"] === undefined) {
        set_errors("No run ID is set - you need to upload files to get a run ID.")
        return
    }

    let form_data = new FormData(form_element)
    response = await fetch(API_ROOT + 'start_simulation_from_form/' + run_status["run_id"], {
        method: 'POST',
        body: form_data
    })
    result = await response.json()
    add_to_query_list("start_simulation_from_form", response, result)
    if (response.status >= 400) {
        set_errors("Error: " + result["error"])
        return
    }

    if (run_status["interval_id"]) {
        clearInterval(run_status["interval_id"]);
    }
    run_status["interval_id"] = setInterval(check_status, 10 * 1000, run_status["run_id"])
}

function main() {
    // attaching listeners to elements that exist when the JS is being executed
    document.getElementById('parameters-form').onsubmit = async function(event) {
        event.preventDefault()
        start_simulation_from_form(this)
    }

    // events to handle when the document is ready
    document.onreadystatechange = async function(event) {
        if (document.readyState == "complete") {
            // fetch content for the user's NC root dir, but only if the user is logged in.
            // spoofing the login status client-side is not a security concern as the API
            // checks authentication anyway
            let logged_in = by_id("nc-logged-in-info")
            if (logged_in) fetch_nc_file_list()
        }
    }
}

main()