#!/usr/bin/python

# write an experiment that creates a new control program.
import os
import sys
import copy

BOREALISPATH = os.environ['BOREALISPATH']
sys.path.append(BOREALISPATH)

from experiment_prototype.experiment_prototype import ExperimentPrototype
import experiments.superdarn_common_fields as scf


class Twofsound(ExperimentPrototype):

    def __init__(self, **kwargs):
        cpid = 3503

        if scf.IS_FORWARD_RADAR:
            beams_to_use = scf.STD_24_FORWARD_BEAM_ORDER
        else:
            beams_to_use = scf.STD_24_REVERSE_BEAM_ORDER

        if scf.opts.site_id in ["cly", "rkn", "inv"]:
            num_ranges = scf.POLARDARN_NUM_RANGES
        if scf.opts.site_id in ["sas", "pgr", "wal"]:
            num_ranges = scf.STD_NUM_RANGES

        tx_freq_1 = scf.COMMON_MODE_FREQ_1
        tx_freq_2 = scf.COMMON_MODE_FREQ_2

        if kwargs:
            if 'freq1' in kwargs.keys():
                tx_freq_1 = int(kwargs['freq1'])

            if 'freq2' in kwargs.keys():
                tx_freq_2 = int(kwargs['freq2'])

        slice_1 = {  # slice_id = 0, the first slice
            "pulse_sequence": scf.SEQUENCE_7P,
            "tau_spacing": scf.TAU_SPACING_7P,
            "pulse_len": scf.PULSE_LEN_45KM,
            "num_ranges": num_ranges,
            "first_range": scf.STD_FIRST_RANGE,
            "intt": scf.INTT_7P_24,  # duration of an integration, in ms
            "beam_angle": scf.STD_24_BEAM_ANGLE,
            "rx_beam_order": beams_to_use,
            "tx_beam_order": beams_to_use,
            "scanbound" : scf.easy_scanbound(scf.INTT_7P_24, beams_to_use),
            "freq" : tx_freq_1, #kHz
            "acf": True,
            "xcf": True,  # cross-correlation processing
            "acfint": True,  # interferometer acfs
        }

        slice_2 = copy.deepcopy(slice_1)
        slice_2['freq'] = tx_freq_2

        list_of_slices = [slice_1, slice_2]
        sum_of_freq = 0
        for slice in list_of_slices:
            sum_of_freq += slice['freq']# kHz, oscillator mixer frequency on the USRP for TX
        rxctrfreq = txctrfreq = int(sum_of_freq/len(list_of_slices))


        super(Twofsound, self).__init__(cpid, txctrfreq=txctrfreq, rxctrfreq=rxctrfreq,
                comment_string='Twofsound classic scan-by-scan')

        self.add_slice(slice_1)

        self.add_slice(slice_2, interfacing_dict={0: 'SCAN'})

