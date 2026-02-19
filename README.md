# Simulation Interface and Management Over Network (SIMON)

## Installation
**Prerequisites: Docker, git**
1. Get a copy of the source files and `cd` into the directory
    * The easiest is to use `git clone --recurse-submodules git@github.com:QuaSi-Software/simon.git`
    * If you use `clone` without `--recurse-submodules` you will need to run `git submodule update --init --recursive` afterwards
    * If you do not wish to use git to get the source files, you will need to fetch the repository in submodule `sim_api/resie` separately and place its files in there.
1. `cp sim_api/config_default.env sim_api/config.env` and edit config for your deployment use case
1. `cp webapp/config_default.env webapp/config.env` and edit config for your deployment use case
1. `cp sim_api/api_config_default.yml sim_api/api_config.yml` and edit config for your deployment use case
1. `cp webapp/webapp_config_default.yml webapp/webapp_config.yml` and edit config for your deployment use case

## Running
1. `cd path/to/simon`
1. `docker compose up`

## Development
General info:
* Changing something in the compose config or the Dockerfiles requires deleting the containers and images and letting them rebuild with compose. The sim API takes a long to rebuild, so try to avoid that if not necessary.
* Changing something in the flask code requires stopping and restarting the container, which is fairly quick.
* Changing something in the JS/CSS and assets doesn't require restarting the container, simply `ctrl+f5` in the browser.

### Debugging
The webapp can be debugged using breakpoints with a remote-attach config in VS Code:
```json
{
    "name": "Python Debugger: Remote Attach SIMON webapp",
    "type": "debugpy",
    "request": "attach",
    "connect": {
        "host": "localhost",
        "port": 5002
    },
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}/webapp",
            "remoteRoot": "/app"
        }
    ]
}
```
This feature is only available with environment variable `FLASK_ENV=development`, which can be set in `config.env`.