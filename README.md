       ____
     _(____)_   __  __ _   _ ___ ___ ___ _  _ 
    (________) |  \/  | | | | __| __|_ _| \| |
     \      /  | |\/| | |_| | _|| _| | || .` |
      \____/   |_|  |_|\___/|_| |_| |___|_|\_|

The repository contains auxiliary scripts to download and compile the ingredients of MUFFIN model, and to run MUFFIN.

Whenever presenting or publishing any results obtained with MUFFIN, please cite the published versions of https://arxiv.org/abs/2301.11894, https://arxiv.org/abs/2511.10487
### Prerequisites
The framework has been tested on Ubuntu 22.04+ and Debian 12 with GCC compiler suite. It depends on the following tools/libraries:
- GCC 8.0+ , however it is better to use a newer version
- CMake 3.16+ (required by SMASH and smash-hadron-sampler)
- ROOT 6.xx  (make sure ROOT installation is compartible with the GCC version in use)
- GNU Scientific Library (GSL) 	2.0+

### Installation

clone the repository, cd into its root directory and run

    bash initialize_MUFFIN.sh

Once the installation is successful,

### Setting up simulation scenarios

**cd into user/ subdirectory**, where you'll find a yaml file bestfit_2030.yaml. In such a file, one declares changes from the default settings found in base parameter files, e.g. different collision energy, centrality, number of events on top of every hydro evolution, fluid-dynamical settings etc, as follows:

    - name: 7_2030_alpha08_beta01_etaparam4    << change the name (same as output sub-sirectory) here
      hydro_base: AuAu_7GeV_base
      hydro:
        snn:              7.7    << change the collision energy here
        b_min:            6.48    << min. impact parameter (the only way to define centrality in this version) 
        b_max:            7.95    << max. impact parameter
        tauMax:           25.0
        frictionModel:    4
        alpha:            0.8
        beta:             0.1
        etaS:             0.0
        etaSparam:        4
        nevents:          1000    << number of initial nuclear configurations used to generate averaged initial state
      sampler:
        number_of_events: 100    << number of hadronic events sampled at particlization
      smash:
        Nevents: 100        << number of final-state hadronic evolutions (should be the same as number_of_events above)


To run 2 test simulations roughly corresponding to 20-30% central Au-Au collisions at sqrt(s)=62.4 and 7.7 GeV, with modifications declared in bestfit_2030.yaml , run

    python3 ../scripts/setup_scenarios.py bestfit_2030.yaml

which will setup subdirectory structures for each simulation in data/ and create corresponding (compact) run script batch_run_${TIMESTAMP}.sh .

### Running the simulations

Take a deep breath and run the generated Bash script:

    ./batch_run_${TIMESTAMP}.sh

exhale, and once the test simulations successfully finish in couple hours, find the generated events in data/${SCENARIO}/smash.output/ . The generated events are split into chunks such that hadron sampling and final-state hadronic cascade are run in 2 parallel processes.
