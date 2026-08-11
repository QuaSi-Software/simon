# Changelog
Lists changes to the code by version.

## SIMON Webapp
The SIMON webapp provides the user interface for running simulations and uses the simulation API in the background.

### Version 0.4.0
* Full integration of ReSiE replacing the placeholder simulation code
  * Implement fetching ReSiE results in frontend
  * Add display of current ReSiE version
* Implement browser-session-persistency for selected NC directory, run ID, status and uploaded files
* Implement reset run button in conjuction with the session-persistent run data
* Implement button to stop polling for simulation results
* Update endpoint fetch_results so it takes the requested file as argument
* Make NC file list highlight the file/directory that is hovered over
* Fix webapp API root not being customizable for installations outside localhost dev installations

### Version 0.3.3
* Improve frontend design and element structure

### Version 0.3.2
* Implement file uploading from NC navigation in frontend to the current simulation run
* Restructure simulation input form to select the input file from the list of uploaded files instead of containing the simulation parameters in the form
* Restructure endpoint fetch_results to also upload the results to the same directory as the input file
* Implement option to debug webapp flask server from VS Code via remote attach
* Extend README with useful information for developers

### Version 0.3.1
* Add a directory navigation of the user's NextCloud file system to the frontend. This is the main element for configuring the simulation input, by selecting files to be uploaded to a simulation run.

### Version 0.3.0
* Implement server-side session storage instead of the default local storage
* Implement authentication flow using oauth with a configured NextCloud instance
  * The authentication tokens acquired during login are persisted in the session as they are required for further requests against the NextCloud APIs

### Version 0.2.2
* Fix path of config file in app construction being relative instead of absolute

### Version 0.2.1
* Implement app config loading from yaml file for webapp
* Implement sending API key in headers for requests to sim_api from webapp, which is required in sim API v0.2.0

### Version 0.2.0
* Implement full simulation workflow with testing simulation implementation of sim API. This includes:
  * A form for configuring the simulation beforehand
  * Starting the simulation
  * Feedback on the status of the simulation
  * Fetching and displaying results once the simulation is complete

### Version 0.1.1
* Set MIT licensing of code
* Implement basic Bootstrap site structure
* Add imprint

### Version 0.1.0
* First version with simple/empty flask app for providing the webapp as SPA

## Simulation API
The simulation API is used by the SIMON webapp internally and is only partially exposed outside of it. As its code is in the same repo it has its own changelog and versions for the python package. Changes that only affect the simulation API without changing any of the SIMON webapp code are not marked as changes in the webapp changelog and are listed here.

### Version 0.3.3
* Update to ReSiE version 1.0.0
  * This required several changes as the package was renamed
* Fix missing widget type mapping for julia type `Integer`
* Add ReSiE version as top-level parameter in SUSI format of parameters endpoint

### Version 0.3.2
* Update to ReSiE version 0.14.5
* Update parameters endpoint to require a format specifier for a number of implemented formats (currently only SUSI, but will be extended in the future)
  * The format determines a number of modifications that are done to the raw results of the parameters JSON as it is produced by ReSiE. These modifications are specific to the format and not ReSiE, thus representing a middle layer between an app/GUI making use of the endpoint and the data that ReSiE contains

### Version 0.3.1
* Update to ReSiE version 0.13.12
* Add endpoint parameters for getting the parameter definitions of ReSiE
  * At the moment this includes only the parameters for the component types. The structure for further additions, e.g. the general simulation parameters, are in place to be added once the corresponding ReSiE functionality has been implemented

### Version 0.3.0
* Full integration of ReSiE replacing the placeholder simulation code
  * The current ReSiE version 0.13.7 is used
  * Add endpoint to get the used ReSiE version
  * Uploaded input files are aliased both for the file name on disk as well as the config file used for simulation. This prevents a number of security vulnerabilities.
  * Logging of the simulations is set up to be specific to the run
* Update download_file endpoint to work with an allowed list of output files

### Version 0.2.1
* Switch config file of sim_api from JSON to YAML.

### Version 0.2.0
* Add simple app config via JSON
* Add API key authorization requirement to all API routes

### Version 0.1.3
* Add endpoint for downloading files
* Fix simulation output files bypassing the file index and therefore not being addressable

### Version 0.1.2
* Implement simulation as calculating Julia sets, for testing purposes
* Fix missing Julia environment parameter when starting scanner

### Version 0.1.1
* Restructure Docker compose structure for customizable configs
* Implement multithreading of scanner and simulation
* Add README with simple installation and usage instructions

### Version 0.1.0
* Switch to more modern pyproject.toml config for editable self-install of the package
* Add/implement routes for:
  * Get run ID
  * Get status of a run
  * Upload file to a run
  * Start the simulation of a run
* Implement scanner that checks for runs ready to simulate and starts the simulation in a thread

### Version 0.0.1
* Set up structure as python package
* Import code from prototyping phase.