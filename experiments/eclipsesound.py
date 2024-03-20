#!/usr/bin/python3

import os
import sys

BOREALISPATH = os.environ['BOREALISPATH']
sys.path.append(BOREALISPATH)

from experiment_prototype.experiment_prototype import ExperimentPrototype
import experiments.superdarn_common_fields as scf

class EclipseSound(ExperimentPrototype):
    """EclipseSound is a modified version of InterleaveSound developed for Wallops
    to observe the 2024-04-08 eclipse. During the first 30 seconds we sweep through 
    every other beam, and during the remaining 30 seconds we step through 5 frequencies
    on 4 beams.
    """
    def __init__(self):
        cpid = 1048

        beams_to_use    = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
        sounding_beams  = [0, 7, 15, 23]

        slices = []
        
        common_scanbound_spacing = 2.5  # seconds
        common_intt_ms = common_scanbound_spacing * 1.0e3 - 100  # reduce by 100 ms for processing

        slices.append({  # slice_id = 0, the first slice
            "pulse_sequence": scf.SEQUENCE_8P,
            "tau_spacing": scf.TAU_SPACING_8P,
            "pulse_len": scf.PULSE_LEN_45KM,
            "num_ranges": scf.STD_NUM_RANGES,
            "first_range": scf.STD_FIRST_RANGE,
            "intt": common_intt_ms,  # duration of an integration, in ms
            "beam_angle": scf.STD_24_BEAM_ANGLE,
            "rx_beam_order": beams_to_use,
            "tx_beam_order": beams_to_use,
            # this scanbound will be aligned because len(beam_order) = len(scanbound)
            "scanbound" : [i * common_scanbound_spacing for i in range(len(beams_to_use))],
            "freq" : scf.COMMON_MODE_FREQ_1, # kHz
            "acf": True,
            "xcf": True,  # cross-correlation processing
            "acfint": True,  # interferometer acfs
            "lag_table": scf.STD_8P_LAG_TABLE,  # lag table needed for 8P since not all lags used.
        })

        sounding_scanbound_spacing = 1.5  # seconds
        sounding_intt_ms = sounding_scanbound_spacing * 1.0e3 - 250

        sounding_scanbound = [30 + i * sounding_scanbound_spacing for i in range(20)]

        # ECLIPSE_FREQS  = [10000, 11000, 12000, 13000, 14000]
        for freq in scf.ECLIPSE_FREQS:
            slices.append({
                "pulse_sequence": scf.SEQUENCE_8P,
                "tau_spacing": scf.TAU_SPACING_8P,
                "pulse_len": scf.PULSE_LEN_45KM,
                "num_ranges": scf.STD_NUM_RANGES,
                "first_range": scf.STD_FIRST_RANGE,
                "intt": sounding_intt_ms,  # duration of an integration, in ms
                "beam_angle": scf.STD_24_BEAM_ANGLE,
                "rx_beam_order": sounding_beams,
                "tx_beam_order": sounding_beams,
                "scanbound" : sounding_scanbound,
                "freq": freq,
                "acf": True,
                "xcf": True,  # cross-correlation processing
                "acfint": True,  # interferometer acfs
                "lag_table": scf.STD_8P_LAG_TABLE,  # lag table needed for 8P since not all lags used
                })

        sum_of_freq = 0
        for slice in slices:
            sum_of_freq += slice['freq']  # kHz, oscillator mixer frequency on the USRP for TX
        rxctrfreq = txctrfreq = int(sum_of_freq / len(slices))

        super(EclipseSound, self).__init__(cpid, txctrfreq=txctrfreq, rxctrfreq=rxctrfreq,
                                              comment_string=EclipseSound.__doc__)

        self.add_slice(slices[0])
        self.add_slice(slices[1], {0: 'SCAN'})
        for slice_num in range(2, len(slices)):
            self.add_slice(slices[slice_num], {1: 'AVEPERIOD'})

