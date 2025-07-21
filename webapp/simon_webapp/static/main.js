API_ROOT = "http://127.0.0.1:5001/"

function by_id(id) {
    return document.getElementById(id)
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

        by_id('run-id').innerText = result["run_id"]

        let item = '<div class="query-result card"><div class="card-body">'
            + '<span>Request: start_simulation</span><br/>'
            + '<span>Code: ' + (response.status ? response.status : 'Error') + '</span><br/>'
            + '<span>Message: ' + (result["message"] ? result["message"] : '') + '</span><br/>'
            + '<span>Error: ' + (result["error"] ? result["error"] : '') + '</span>'
            + '</div></div>'
        by_id('query-list').innerHTML = item + by_id('query-list').innerHTML
    }
}

main()