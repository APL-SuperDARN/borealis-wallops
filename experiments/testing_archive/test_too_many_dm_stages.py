#!/usr/bin/python

# write an experiment that raises an exception

import sys
import os

BOREALISPATH = os.environ['BOREALISPATH']
sys.path.append(BOREALISPATH)

import experiments.superdarn_common_fields as scf
from experiment_prototype.experiment_prototype import ExperimentPrototype
from experiment_prototype.decimation_scheme.decimation_scheme import \
    DecimationScheme, DecimationStage, create_firwin_filter_by_attenuation

class TestExperiment(ExperimentPrototype):

    def __init__(self):
        cpid = 1
        #  Number of decimation stages is greater than options.max_number_of_filtering_stages
        rates = [5.0e6, 1.0e6, 500.0e3, 250.0e3, 125.0e3, 62.5e3, 31.25e3 ] # 7 stages, greater than max of 6
        dm_rates = [5, 2, 2, 2, 2, 2, 2]
        transition_widths = [150.0e3, 80.0e3, 40.0e3, 20.0e3, 10.0e3, 5.0e3, 1.0e3]
        cutoffs = [20.0e3, 20.0e3, 10.0e3, 10.0e3, 5.0e3, 5.0e3, 5.0e3]
        ripple_dbs = [150.0, 80.0, 70.0, 35.0, 20.0, 15.0, 10.0]
        scaling_factors = [10.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
        all_stages = []
        for stage in range(0, len(rates)):
            filter_taps = list(
                scaling_factors[stage] * create_firwin_filter_by_attenuation(
                    rates[stage], transition_widths[stage], cutoffs[stage],
                    ripple_dbs[stage]))
            all_stages.append(DecimationStage(stage, rates[stage],
                              dm_rates[stage], filter_taps))

        # changed from 10e3/3->10e3
        decimation_scheme = (DecimationScheme(rates[0], rates[-1]/dm_rates[-1], stages=all_stages))
        super(TestExperiment, self).__init__(
            cpid, output_rx_rate=decimation_scheme.output_sample_rate,
            decimation_scheme=decimation_scheme)


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
