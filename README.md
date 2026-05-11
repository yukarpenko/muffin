The repository contains auxiliary scripts to download and compile the ingredients of MUFFIN model, and to run MUFFIN.

Whenever presenting or publishing any results obtained with MUFFIN, please cite the published versions of https://arxiv.org/abs/2301.11894, https://arxiv.org/abs/2511.10487

### Installation

clone the repository, cd into its root directory and run

    bash initialize_MUFFIN.sh

Once the installation is successful,

### Setting up simulation scenarios

**cd into user/ subdirectory**, where you'll find a yaml file bestfit_2030.yaml. In such a file, one declares changes from the default settings found in base parameter files, e.g. different collision energy, centrality, number of events on top of every hydro evolution, fluid-dynamical settings etc.

To run 2 test simulations roughly corresponding to 20-30% central Au-Au collisions at sqrt(s)=62.4 and 7.7 GeV, with modifications declared in bestfit_2030.yaml , run

    python3 ../scripts/setup_scenarios.py bestfit_2030.yaml

which will setup subdirectory structures for each simulation in data/ and create corresponding (compact) run script batch_run_${TIMESTAMP}.sh . Take a deep breath and run the generated Bash script:

    ./batch_run_${TIMESTAMP}.sh

exhale, and once the test simulations successfully finish in couple hours, find the generated events in data/${SCENARIO}/smash.output/ . The generated events are split into chunks such that hadron sampling and final-state hadronic cascade are run in 2 parallel processes.
