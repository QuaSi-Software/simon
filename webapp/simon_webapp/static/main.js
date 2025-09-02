API_ROOT = "http://localhost:5001/"

run_status = {}

function by_id(id) {
    return document.getElementById(id)
}

function by_cl(class_name) {
    return Array.from(document.getElementsByClassName(class_name))
}

function format_filename(filename, full_path) {
    if (filename.startsWith("/")) {
        filename = filename.slice(1);
    }
    if (filename[filename.length-1] === "/") {
        filename = filename.slice(0,filename.length-1);
    }

    if (full_path) {
        return decodeURI(filename)
    }

    let splitted = filename.split("/")
    return decodeURI(splitted[splitted.length - 1]);
}

async function fetch_results(run_id) {
    let response = await fetch(API_ROOT + 'fetch_results/' + run_id, {method: 'GET'})
    let result = {}
    if (response.status >= 400) {
        result = response.json()
    }
    let item = '<div class="query-result card"><div class="card-body">'
            + '<span>Request: fetch_results</span><br/>'
            + '<span>Code: ' + (response.status ? response.status : 'Error') + '</span><br/>'
            + '<span>Message: ' + (result["message"] ? result["message"] : '') + '</span><br/>'
            + '<span>Error: ' + (result["error"] ? result["error"] : '') + '</span>'
            + '</div></div>'
    by_id('query-list').innerHTML = item + by_id('query-list').innerHTML

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

    run_status["status"] = result["code"]
    by_id('run-status').innerText = run_status["status"]

    let item = '<div class="query-result card"><div class="card-body">'
            + '<span>Request: run_status</span><br/>'
            + '<span>Code: ' + (response.status ? response.status : 'Error') + '</span><br/>'
            + '<span>Message: ' + (result["message"] ? result["message"] : '') + '</span><br/>'
            + '<span>Error: ' + (result["error"] ? result["error"] : '') + '</span>'
            + '</div></div>'
    by_id('query-list').innerHTML = item + by_id('query-list').innerHTML

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
        splitted = splitted.slice(0,-2)
        new_val = splitted.join("/")
    }
    by_id("nc-current-dir").setAttribute("data-dirname", new_val)
    by_id("nc-current-dir").innerText = "/" + format_filename(new_val, true)
    fetch_nc_file_list()
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

    let items = []
    files.sort((a, b) => {
        if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
        return a.name.localeCompare(b.name)
    }).forEach(item => {
        if (item.name != "/" && item.name != curr_dir) {
            let prefix = item.is_dir ? "|\>&nbsp;" : "|&nbsp;&nbsp;"
            items.push(
                "<li"
                + (item.is_dir ? " class='nc-file-list-dir'" : "")
                + (item.is_dir ? " data-dirname='" + item.name + "'" : "")
                + ">"
                + prefix + format_filename(item.name, false)
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

    by_id("nc-file-list-blocker").classList.add("hidden")
}

async function start_simulation() {
    let form_data = new FormData(this)
    let response = await fetch(API_ROOT + 'start_simulation', {
        method: 'POST',
        body: form_data
    })
    let result = await response.json()

    run_status["run_id"] = result["run_id"]
    by_id('run-id').innerText = run_status["run_id"]

    let item = '<div class="query-result card"><div class="card-body">'
        + '<span>Request: start_simulation</span><br/>'
        + '<span>Code: ' + (response.status ? response.status : 'Error') + '</span><br/>'
        + '<span>Message: ' + (result["message"] ? result["message"] : '') + '</span><br/>'
        + '<span>Error: ' + (result["error"] ? result["error"] : '') + '</span>'
        + '</div></div>'
    by_id('query-list').innerHTML = item + by_id('query-list').innerHTML

    if (run_status["interval_id"]) {
        clearInterval(run_status["interval_id"]);
    }
    run_status["interval_id"] = setInterval(check_status, 10 * 1000, run_status["run_id"])
}

function main() {
    // attaching listeners to elements that exist when the JS is being executed
    document.getElementById('parameters-form').onsubmit = async function(event) {
        event.preventDefault()
        start_simulation()
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