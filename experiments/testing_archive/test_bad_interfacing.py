#!/usr/bin/python

# write an experiment that raises an exception

import copy
import sys
import os

BOREALISPATH = os.environ['BOREALISPATH']
sys.path.append(BOREALISPATH)

import experiments.superdarn_common_fields as scf
from experiment_prototype.experiment_prototype import ExperimentPrototype


class TestExperiment(ExperimentPrototype):

    def __init__(self):
        cpid = 1
        super(TestExperiment, self).__init__(cpid)

        if scf.IS_FORWARD_RADAR:
            beams_to_use = scf.STD_24_FORWARD_BEAM_ORDER
        else:
            beams_to_use = scf.STD_24_REVERSE_BEAM_ORDER

        if scf.opts.site_id in ["cly", "rkn", "inv"]:
            num_ranges = scf.POLARDARN_NUM_RANGES
        if scf.opts.site_id in ["sas", "pgr", "wal"]:
            num_ranges = scf.STD_NUM_RANGES

        slice_1 = {  # slice_id = 0, there is only one slice.
            "pulse_sequence": scf.SEQUENCE_7P,
            "tau_spacing": scf.TAU_SPACING_7P,
            "pulse_len": scf.PULSE_LEN_45KM,
            "num_ranges": num_ranges,
            "first_range": scf.STD_FIRST_RANGE,
            "intt": 3500,  # duration of an integration, in ms
            "beam_angle": scf.STD_24_BEAM_ANGLE,
            "rx_beam_order": beams_to_use,
            "tx_beam_order": beams_to_use,
            "scanbound": [i * 3.5 for i in range(len(beams_to_use))], #1 min scan
            "freq" : scf.COMMON_MODE_FREQ_1, #kHz
            "acf": True,
            "xcf": True,  # cross-correlation processing
            "acfint": True,  # interferometer acfs
        }
        self.add_slice(slice_1)
        # Interfacing between slices is not internally consistent. Here we add slice_2 and slice_3,
        # with CONCURRENT interfacing to slice_1, but then try to interface 2 and 3 together as SCAN.
        slice_2 = copy.deepcopy(slice_1)
        slice_3 = copy.deepcopy(slice_1)
        slice_3['freq'] = scf.COMMON_MODE_FREQ_2 + 1
        self.add_slice(slice_2, interfacing_dict={0:'CONCURRENT'})
        self.add_slice(slice_3, interfacing_dict={0:'CONCURRENT', 1:'SCAN'})

