# Changelog
Lists changes to the code by version.

## SIMON Webapp
The SIMON webapp provides the user interface for running simulations and uses the simulation API in the background.

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
The simulation API is used by the SIMON webapp internally and is not exposed outside of it. As its code is in the same repo it has its own changelog and versions for the python package.

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