# Changelog
Lists changes to the code by version.

## SIMON Webapp
No version released yet

## Simulation API
The simulation API is used by the SIMON webapp internally and is not exposed outside of it. As its code is in the same repo it has its own changelog and versions for the python package.

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