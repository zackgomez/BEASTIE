#!/usr/bin/env python

###############################################
# usage: python run_config_NA19247.py
###############################################
import BEASTIE

if __name__ == "__main__":
    config = BEASTIE.load_configuration("parameters_NA19247.cfg")
    BEASTIE.run(config)