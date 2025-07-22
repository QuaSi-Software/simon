API_ROOT = "http://127.0.0.1:5001/"

run_status = {}

function by_id(id) {
    return document.getElementById(id)
}

async function check_status(run_id) {
    console.log("check_status called")
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
    }
}

function main() {
    document.getElementById('parameters-form').onsubmit = async function(event) {
        event.preventDefault()

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
}

main()