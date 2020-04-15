#!/usr/bin/env python3
# coding: utf-8
"""@package nec_sd_generator

Designed to generate wire structures/loads/etc for using with a NEC program like 4nec2 or eznec.
Part 3 of the NEC2 users manual was referenced heavily (http://www.nec2.org/other/nec2prt3.pdf)

Author: Kevin Krieger
Copyright 2020 SuperDARN Canada
"""

import argparse
import sys
import math

# Used to calculate the minimum number of segments per wire structure
from scipy.constants import speed_of_light

# Very important that this global variable is kept up-to-date and
# consistent throughout. It is a unique id for each wire structure
wire_number = 0
min_frequency = 8e6  # Use to calculate min # of segments per wire
aluminum_conductivity = 3.5e7  # Siemen's per meter at 20 degrees C
copper_conductivity = 5.96e7  # Siemen's per meter at 20 degrees C
annealed_copper_conductivity = 5.8e7  # Siemen's per meter at 20 degrees C


# TODO: Docstrings for all


class Reflector(object):
    """
    Reflector wire class used to describe reflector fence wires in the antenna array system
    as NEC strings
    """

    def __init__(self, length_m, spacing_m, start_height_m=15.0, num_wires=0, awg=13, angle=45,
                 global_x=0.0, global_y=0.0, global_z=0.0):
        """
        :param length_m: The length of the reflector wires in meters
        :param spacing_m: The straight line distance between successive reflector wires in meters
        :param start_height_m: The starting height of the first reflector wire. Default 15, meters
        :param num_wires: The number of reflector fence wires. If not given, the max is calculated
        :param awg: The wire gauge in American Wire Gauge of the reflector wires. Defaults to 13
        :param angle: The angle the reflector fence makes with the ground in degrees
        :raises ValueError when the spacing_m, angle and num_wires are incompatible
        """
        # TODO: if spacing_m, angle and num_wires are incompatible (i.e. wires in the ground)
        # raise ValueError

        self.reflector_wires = []
        radius = get_mm_radius_from_awg(awg) / 1000.0
        if num_wires == 0:
            # Use spacing to determine the amount of wires given that the reflector
            # fence starts above the antennas and goes down at a given angle until the ground
            raise NotImplementedError("Please specify # of wires, auto calculation not implemented.")
        else:
            # We are given the number of wires, so place them with the spacing and angle given
            for reflector_wire in range(0, num_wires):
                x1 = -length_m / 2.0
                x2 = length_m / 2.0
                y = -reflector_wire * math.cos(angle * math.pi / 180.0) * spacing_m
                z = reflector_wire * math.sin(angle * math.pi / 180.0) * spacing_m
                self.reflector_wires.append(Wire(x1 + global_x, y + global_y,
                                                 start_height_m - z + global_z, x2 + global_x,
                                                 y + global_y, start_height_m - z + global_z,
                                                 radius))

    def __repr__(self):
        """
        Represent the Reflector object as a string
        :return: String representing the reflector object in a format NEC understands
        """
        return_string = ""
        for reflector_wire in self.reflector_wires:
            return_string += str(reflector_wire) + "\n"
        return return_string.replace('\n', '\r\n')


class TransmissionLine(object):
    """
    TransmissionLine class used to describe ideal transmission lines in the antenna array system.
    These are particularly useful for modeling LogPeriodic antennas, which have a transmission line
    down the length of the boom, used to feed each dipole with alternating phase.

    :param tag1: Tag/wire number connected to end 1 of the transmission line
    :param segment1: Segment number of the tag/wire that end 1 is connected to
    :param tag2: Tag/wire number connected to end 2 of the transmission line
    :param segment2: Segment number of the tag/wire that end 2 is connected to
    :param crossed: Boolean, Should the line be 'twisted' to present 180 deg phase dif between tags?
    :param impedance: Characteristic impedance of the transmission line in Ohms
    :param length: The length in meters of the transmission line, if 0.0, NEC uses straight line distance
    """

    def __init__(self, tag1, segment1, tag2, segment2, crossed, impedance=50.0, length=0.0):
        # See the NEC documentation for crossed transmission lines
        if crossed:
            impedance *= -1
        self.transmissionline = "TL {} {} {} {} {} {} 0.0 0.0 0.0 0.0".format(tag1, segment1, tag2,
                                                                              segment2, impedance, length)

    def __repr__(self):
        """
        :return: A string representation of the transmission line object that NEC will understand
        """
        return self.transmissionline


class Feedline(object):
    """
    Feedline class used to describe feedlines in the antenna array system
    """

    def __init__(self):
        raise NotImplementedError("Feedline objects have not been implemented.")


class Balun(object):
    """
    Balun class used to describe baluns (impedance matching between the feedlines and the antennas)
    in the antenna array system
    """

    def __init__(self):
        raise NotImplementedError("Balun objects have not been implemented.")


class Load(object):
    """
    Load class used to describe NEC loads in the antenna array system (real or complex)
    """

    def __init__(self, tag, start_segment=0, end_segment=0, impedance_real=100, impedance_imag=0):
        """
        Applies a NEC compatible load to a given tag number and set of segments with given
        impedance made up of a complex impedance. If start_segment and end_segment
        are blank or 0, then the load applies to all segments of the tag
        :param tag: Which wire number does the load apply to?
        :param start_segment: Which start segment of the tag to apply the load to
        :param end_segment: Which end segment of the tag to apply the load to
        :param impedance_real: The real part of the complex impedance for the load
        :param impedance_imag: The imaginary part of the complex impedance for the load
        """

        self.load = "LD 4 {} {} {} {} {}".format(tag, start_segment, end_segment,
                                                 impedance_real, impedance_imag)

    def __repr__(self):
        """
        Represent the Load object as a string that NEC understands.
        :return: LD NEC string representing the load object
        """
        return self.load


class Source(object):
    """
    Source class used to describe NEC sources in the antenna array system (excitations)
    """

    def __init__(self, tag, segment, excitation_real=1.0, excitation_imag=0.0, current_source=True):
        """
        Create a NEC source excitation. Either create a current source if current_source is True
        or create a voltage source otherwise. Defaults to current_source, only change this if you
        know what you are doing.
         The 4nec2 current source was added to the program in version 4.x and they are not described in
        the NEC users manual. It appears that voltage sources do not have an effect on this simulation,
        therefore current sources must be used. If using a NEC that isn't compatible with this card,
        then it can be faked. See this page: http://owenduffy.net/blog/?p=3561 or the 4nec2 user manual.

        :param tag: Which tag/wire to place the excitation on?
        :param segment: Which segment of the tag/wire to place the excitation on?
        :param excitation_real: Real part of the voltage or current
        :param excitation_imag: Imaginary part of the voltage or current
        :param current_source: If set to True, then this will be a current source. Default True
        """
        if current_source:
            # 4nec2 doesn't like 0 for the current source values, so we must use a very small number instead
            if excitation_real == 0:
                excitation_real += 1e-10
            if excitation_imag == 0:
                excitation_imag += 1e-10
            self.excitation = "EX 6 {} {} 0 {} {}".format(tag, segment, excitation_real, excitation_imag)
        else:
            self.excitation = "EX 0 {} {} 0 {} {}".format(tag, segment, excitation_real, excitation_imag)

    def __repr__(self):
        """
        Represent the excitation object as a string that NEC understands.
        :return: EX NEC string representing the excitation object
        """
        return self.excitation


class Wire(object):
    """
    Wire class used to describe NEC wire structures. Create wire structures, translate them,
    rotate them
    """

    def __init__(self, x1=0.0, y1=0.0, z1=0.0, x2=0.0, y2=0.0, z2=0.0, radius=0.000127, segments=0):
        """
        Since each wire consists of two points and a line between them in 3d space, we can describe
        a wire by giving two 3d points x1, y1, z1 and x2, y2, z2. It also has a finite radius (in m)
        and NEC splits wire structures up into segments for calculations.
        * Note that the global wire_number variable is modified in this function *

        :param x1: Point 1 x coordinate
        :param y1: Point 1 y coordinate
        :param z1: Point 1 z coordinate
        :param x2: Point 2 x coordinate
        :param y2: Point 2 y coordinate
        :param z2: Point 2 z coordinate
        :param radius: Radius of the wire structure in meters
        :param segments: The NEC engine splits up wire structures into segments for calculations,
        This defaults to an appropriate number of segments given the minimum frequency used in the
        simulation but can also be given as an argument to this function.
        """
        global wire_number
        wire_number += 1
        wire_length = math.sqrt(
            (z2 - z1) * (z2 - z1) + (y2 - y1) * (y2 - y1) + (x2 - x1) * (x2 - x1))
        # See nec2.org/part_3/secii.html for info on how long segments should be relative to wl
        # segment length delta should be < 0.1 wavelength or < 0.05 wavelength on critical sections
        if segments is 0:
            segment_length = 0.05 * speed_of_light / min_frequency
            segments = int(wire_length / segment_length)
            if segments % 2 == 0:
                segments += 1
        self.wire_structure = {'wire_number': wire_number, 'segments': segments, 'x1': x1, 'y1': y1,
                               'z1': z1, 'x2': x2, 'y2': y2, 'z2': z2, 'radius': radius}

    def get_mid_segment(self):
        """
        :return: The middle segment number
        :raises: ValueError when there are not an odd number of segments
        """
        if self.wire_structure['segments'] % 2 is 0:
            raise ValueError("There are an even number of segments: {}, "
                             "middle segment DNE.".format(self.wire_structure['segments']))
        return 1 + int(self.wire_structure['segments'] / 2)

    def get_wire_number(self):
        """
        :return: The unique wire number
        """
        return self.wire_structure['wire_number']

    def translate(self, x, y, z):
        """
        Translate a wire structure by x, y, z meters

        :param x: Translate the wire structure in the x direction by this many meters
        :param y: Translate the wire structure in the y direction by this many meters
        :param z: Translate the wire structure in the z direction by this many meters
        """
        self.wire_structure['x1'] += x
        self.wire_structure['y1'] += y
        self.wire_structure['z1'] += z
        self.wire_structure['x2'] += x
        self.wire_structure['y2'] += y
        self.wire_structure['z2'] += z

    def rotate(self, alpha, beta, gamma):
        """
        Rotate the wire structure first by alpha about the x axis, then by beta about the y axis,
        then by gamma about the z axis.
        :param alpha: Rotate alpha degrees about the x axis
        :param beta: Rotate beta degrees about the y axis
        :param gamma: Rotate gamma degrees about the z axis
        """
        self.rotate_x_axis(alpha)
        self.rotate_y_axis(beta)
        self.rotate_z_axis(gamma)

    def rotate_x_axis(self, alpha):
        """
        Rotate the wire structure about the x axis by alpha degrees
        :param alpha: Rotate alpha degrees about the x axis
        """
        raise NotImplementedError("Wire rotations are not implemented")

    def rotate_y_axis(self, beta):
        """
        Rotate the wire structure about the y axis by beta degrees
        :param beta: Rotate beta degrees about the y axis
        """
        raise NotImplementedError("Wire rotations are not implemented")

    def rotate_z_axis(self, gamma):
        """
        Rotate the wire structure about the z axis by gamma degrees
        :param gamma: Rotate gamma degrees about the z axis
        """
        raise NotImplementedError("Wire rotations are not implemented")

    def __repr__(self):
        """
        :return: A string representation of the wire structure
        """
        nec_string = "GW {} {} ".format(self.wire_structure['wire_number'],
                                        self.wire_structure['segments'])
        nec_string += "{} {} {} {} {} {} {}".format(self.wire_structure['x1'],
                                                    self.wire_structure['y1'],
                                                    self.wire_structure['z1'],
                                                    self.wire_structure['x2'],
                                                    self.wire_structure['y2'],
                                                    self.wire_structure['z2'],
                                                    self.wire_structure['radius'])
        self.wire_structure_string = nec_string
        return self.wire_structure_string


class LogPeriodic(object):
    """
    Class to describe a Log Periodic antenna frequently used in SuperDARN radar arrays.

    ** NOTE ** The ASCII representation below shows the electrical connections from the feedpoint
    to each element in a crosswise manner. For example: element 1 is fed on the left with the
    positive feedpoint, then element 2 is fed on the right with the positive feedpoint,
    then element 3 on the left with the positive feedpoint, etc. This is represented with the 'x's.

    The example shown represents the Sabre Communications Corporation Mode 610
    Log Periodic antenna, used in many SuperDARN installations across the world.
    See https://www.antenna.be/sab-610.html

Element #        (+)feed point(-)        radius (m)  Total length (m)    separation from next (m)
1                 -----| |-----         0.005       6.04                0.725
2                ------ x ------        0.0065      6.7                 0.86
3               ------- x -------       0.01        7.57                1.005
4              -------- x --------      0.0125      8.46                1.175
5             --------- x ---------     0.0125      9.49                1.4
6            ---------- x ----------    0.16        10.55               1.515
7           ----------- x -----------   0.16        11.87               1.705
8          ------------ x ------------  0.19        13.37               1.94
9        -------------- x --------------0.19        15.38               1.305
10       -------------- x --------------0.19        15.4
                       | |
                       ~~~
                    Stub Coil

    """

    def __init__(self, height=15.0, global_x=0.0, global_y=0.0, global_z=0.0,
                 current_real=1.0, current_imag=0.0):
        """
        :param height: Height above the ground, typically 15m
        :param global_x: Absolute location in x dimension in meters
        :param global_y: Absolute location in y dimension in meters
        :param global_z: Absolute location in z dimension in meters
        :param current_real: The real part of the current source
        :param current_imag: The imaginary part of the current source
        """

        self.drivens = []

        # TODO: Figure out radius of each element. Numbers above need verification. Use 1cm for now
        radius = 0.01

        # For modeling, number of segments should be minimum of 11 on smallest element for
        # accurate high frequency modeling. Then each longer element should have more segments
        # TODO: Ensure there are enough segments, don't hardcode it
        self.drivens.append(Wire(-6.04 / 2.0, 0.0, height, 6.04 / 2.0, 0.0, height, radius, 13))

        # One excitation will be placed at the feed point at the apex (smallest element) of the LPDA
        # So we can add that now when we know our only wire/element is the smallest one
        # then create the rest of the driven elements
        self.excitation = Source(self.drivens[0].get_wire_number(),
                                 self.drivens[0].get_mid_segment(),
                                 current_real, current_imag)

        self.drivens.append(Wire(-6.70 / 2.0, 0.725, height, 6.70 / 2.0, 0.725, height, radius, 15))
        self.drivens.append(Wire(-7.57 / 2.0, 1.585, height, 7.57 / 2.0, 1.585, height, radius, 17))
        self.drivens.append(Wire(-8.46 / 2.0, 2.59, height, 8.46 / 2.0, 2.59, height, radius, 19))
        self.drivens.append(Wire(-9.49 / 2.0, 3.765, height, 9.49 / 2.0, 3.765, height, radius, 21))
        self.drivens.append(Wire(-10.55 / 2.0, 5.165, height, 10.55 / 2.0, 5.165, height, radius, 23))
        self.drivens.append(Wire(-11.87 / 2.0, 6.68, height, 11.87 / 2.0, 6.68, height, radius, 25))
        self.drivens.append(Wire(-13.37 / 2.0, 8.385, height, 13.37 / 2.0, 8.385, height, radius, 27))
        self.drivens.append(Wire(-15.38 / 2.0, 10.325, height, 15.38 / 2.0, 10.325, height, radius, 29))
        self.drivens.append(Wire(-15.40 / 2.0, 11.63, height, 15.40 / 2.0, 11.63, height, radius, 31))

        self.transmissionlines = []

        # Go through each driven element and find the next driven element, so we can place a transmission line
        # between them, connecting to the middle segment and alternating phase appropriately.
        for index, driven in enumerate(self.drivens):
            # If this is the first driven element, go to the next one
            if index is 0:
                continue

            # Get the two wires' numbers and middle segments
            wire_num = driven.get_wire_number()
            mid_segment = driven.get_mid_segment()
            prev_wire_num = self.drivens[index - 1].get_wire_number()
            prev_mid_segment = self.drivens[index - 1].get_mid_segment()
            tl = TransmissionLine(prev_wire_num, prev_mid_segment, wire_num, mid_segment, True)
            self.transmissionlines.append(tl)

        # Finally, we need another transmission line to connect to our stub coil
        # A stub at HF can just be a short of the longest element with a 6 inch jumper.
        # A stub at VHF and UHF is calculated via: Z_t = Lambda_max/8
        # TODO: Implement the stub coil

        # TODO: Implement the calculations for characteristic values for LPDAs
        # self.tau = self.calculate_tau()
        # self.sigma = self.calculate_sigma()
        # self.alpha = self.calculate_alpha()
        self.tau = 0
        self.sigma = 0
        self.alpha = 0
        self.stub_length_m = 0

        self.comment_string = "CM Log-Periodic\n" \
                              "CM Height: {} m\n" \
                              "CM Tau: {}\n" \
                              "CM Alpha: {} deg\n" \
                              "CM Sigma: {}\n" \
                              "CM Stub length: {} m\n" \
                              "CE\n".format(height, self.tau, (180 / math.pi) * self.alpha,
                                            self.sigma, self.stub_length_m)

    def calculate_alpha(self):
        """
        Using the geometry of the antenna elements, calculate the parameter represented by
        the lower-case greek letter alpha. Alpha is equal to one-half of the angle at the apex (pointy-bit)
        if you draw a triangle around the envelope of the elements.
        :return: alpha, a floating point number in radians
        """
        raise NotImplementedError("LogPeriodic objects have not been implemented.")

    def calculate_sigma(self):
        """
        Using the geometry of the antenna elements, calculate the parameter represented by
        the lower-case greek letter sigma. Sigma is equal to the relative spacing of the elements.
        :return: sigma, unitless. The ratio of: distance between two elements and 2x the length of longer element
        """
        raise NotImplementedError("LogPeriodic objects have not been implemented.")

    def calculate_tau(self):
        """
        Using the geometry of the antenna elements, calculate the parameter represented by
        the lower-case greek letter tau. Tau is equal to the ratio of the lengths of the elements,
        or the ratio of the distance between successive elements. Note  that Tau is less than 1, so
        the ratio measures the longer element in the denominator.
        :return: tau, unitless. The ratio of the distance between successive elements
        """
        raise NotImplementedError("LogPeriodic objects have not been implemented.")

    def repr_drivens(self):
        """
        :return: A NEC string representation of the geometry of the Log-Periodic drivens for simulation
        """
        value = ""
        for driven in self.drivens:
            value += "{}\r\n".format(driven)
        return value

    def repr_geometry(self):
        """
        :return: A NEC string representation of the geometry of the Log-Periodic for simulation.
        """
        return self.repr_drivens()

    def repr_loads(self):
        """
        :return: A NEC string representation of the loads for the Log-Periodic for simulation
        """
        return ""

    def repr_transmissionlines(self):
        """
        :return: A NEC string representation of the transmission lines for the Log-Periodic for simulation
        """
        value = ""
        for transmissionline in self.transmissionlines:
            value += "{}\r\n".format(transmissionline)
        return value

    def repr_excitations(self):
        """
        :return: A NEC string representation of the excitations for the Log-Periodic for simulation
        """
        return "{}\r\n".format(self.excitation)

    def repr_comment_string(self):
        """
        :return: A human readable NEC comment string describing some characteristics of the Log-Periodic
        """
        return "{}\r\n".format(self.comment_string)


class YAGI(object):
    """
    Class to describe a YAGI antenna. Typically consists of several elements on a boom, with one of
    the elements being driven and the rest are either reflectors or directors.
    Example shown is the A50-6S from Cushcraft:
            Distance            Element name        Length (cm)     Distance to end of boom (cm)
            5.08cm|
            ------|------       Director #4         59.1            5.08
                  |
            174cm |
                  |
           -------|-------      Director #3         71.1            179.08
                  |
           148.6cm|
          --------|--------     Director #2         72.4            332.76
                  |
           147cm  |
          --------|--------     Director #1         74.9            479.76
           60cm   |
         ---------|---------    Driven element      76.2            539.76
           68.6cm |
        ----------|----------   Reflector           88.9            608.36
    """

    def __init__(self, radius=0.0175, height=15.0, global_x=0.0, global_y=0.0, global_z=0.0,
                 current_real=1.0, current_imag=0.0):
        """
        :param radius: Radius of elements, in meters
        :param height: Height above the ground, typically 15m
        :param global_x: Absolute location in x dimension in meters
        :param global_y: Absolute location in y dimension in meters
        :param global_z: Absolute location in z dimension in meters
        :param current_real: The real part of the current source
        :param current_imag: The imaginary part of the current source
        """
        self.comment_string = "CM YAGI\n" \
                              "CM Height: {} m\n" \
                              "CE\n".format(height)
        self.directors = []
        self.reflectors = []
        self.drivens = []

        self.directors.append(Wire(-0.749 / 2.0, 4.7976, height, 0.749 / 2.0, 4.7976, height, radius))
        self.directors.append(Wire(-0.724 / 2.0, 3.3276, height, 0.724 / 2.0, 3.3276, height, radius))
        self.directors.append(Wire(-0.711 / 2.0, 1.7908, height, 0.711 / 2.0, 1.7908, height, radius))
        self.directors.append(Wire(-0.591 / 2.0, 0.0508, height, 0.591 / 2.0, 0.0508, height, radius))
        self.directors.append(Wire(-0.591 / 2.0, 0.0508, height, 0.591 / 2.0, 0.0508, height, radius))

        self.reflectors.append(Wire(-0.889 / 2.0, 6.0836, height, 0.889 / 2.0, 6.0836, height, radius))

        self.drivens.append(Wire(-0.762 / 2.0, 5.3976, height, 0.762 / 2.0, 5.3976, height, radius))

        # TODO: Implement translation, for global x,y,z coords.
        wire_num = self.middlewire.get_wire_number()
        mid_segment = self.middlewire.get_mid_segment()
        self.excitation = Source(wire_num, mid_segment, current_real, current_imag)

    def repr_directors(self):
        """
        :return: A NEC string representation of the geometry of the YAGI directors for simulation
        """
        value = ""
        for director in self.directors:
            value += "{}\r\n".format(director)
        return value

    def repr_reflectors(self):
        """
        :return: A NEC string representation of the geometry of the YAGI reflectors for simulation
        """
        value = ""
        for reflector in self.reflectors:
            value += "{}\r\n".format(reflector)
        return value

    def repr_driven(self):
        """
        :return: A NEC string representation of the geometry of the YAGI drivens for simulation
        """
        value = ""
        for driven in self.drivens:
            value += "{}\r\n".format(driven)
        return value

    def repr_geometry(self):
        """
        :return: A NEC string representation of the geometry of the YAGI for simulation
        """
        value = "{}\r\n{}\r\n{}".format(self.repr_directors(), self.repr_driven(),
                                        self.repr_reflectors())
        return value

    def repr_loads(self):
        """
        :return: A NEC string representation of the loads for the YAGI
        """
        return ""

    def repr_excitations(self):
        """
        :return: A NEC string representation of the excitations for the YAGI
        """
        return "{}\r\n".format(self.excitation)

    def repr_transmissionlines(self):
        """
        :return: A NEC string representation of the transmission lines for the YAGI
        """
        return ""

    def repr_comment_string(self):
        """
        :return: A human readable NEC comment string describing some characteristics of the YAGI
        """
        return "{}\r\n".format(self.comment_string)


class TTFD(object):
    """
    Class to describe a TTFD (Twin-Terminated Folded Dipole) antenna frequently used in
    SuperDARN radar arrays. Typically consists of 7 wire structures, 2 loads and 1 balun.
    Nominal dimensions are: 8m for the top wire and bottom wires, 12m for the width,  100Ohms for
    the loads, and 1.5m for the spacing between the top to middle wires.

                    top wire
          ---------------Load--------------
        /                                   \
      /              width                    \
    x------------------Balun-------------------x
      \                                      /
        \                                  /
          -------------Load---------------
                    bottom wire

    """

    def __init__(self, wire_gauge=13, height=10.0, termination=100.0,
                 mid_width=12.0, top_width=8.0, wire_spacing=1.5,
                 global_x=0.0, global_y=0.0, global_z=0.0,
                 current_real=1.0, current_imag=0.0):
        """
        :param wire_gauge: Gauge of the wire used in AWG (American Wire Gauge) typically 13
        :param height: Height above the ground, typically 10m
        :param termination: Load impedance, typically 100Ohms
        :param mid_width: Middle wire structure width, typically 12m
        :param top_width: Top and bottom wire structure widths, typically 8m
        :param wire_spacing: Spacing between top and middle wires, typically 1.5m
        :param global_x: Absolute location in x dimension in meters
        :param global_y: Absolute location in y dimension in meters
        :param global_z: Absolute location in z dimension in meters
        :param current_real: The real part of the current source
        :param current_imag: The imaginary part of the current source
        """
        self.wire_radius_m = get_mm_radius_from_awg(wire_gauge) / 1000.0
        self.comment_string = "CM SuperDARN TTFD\n" \
                              "CM Height: {} m\n" \
                              "CM Wire gauge: {} AWG\n" \
                              "CM Termination: {} Ohms\n" \
                              "CM Mid wire width: {} m\n" \
                              "CM Top/bottom wire width: {} m\n" \
                              "CM Wire spacing: {} m\n" \
                              "CE\n".format(height, wire_gauge, termination,
                                            mid_width, top_width, wire_spacing)
        self.topleftwire = Wire(-mid_width / 2.0, 0.0, height,
                                -top_width / 2.0, 0.0, wire_spacing + height,
                                self.wire_radius_m)
        self.topleftwire.translate(global_x, global_y, global_z)
        self.topwire = Wire(-top_width / 2.0, 0.0, wire_spacing + height,
                            top_width / 2.0, 0.0, wire_spacing + height, self.wire_radius_m)
        self.topwire.translate(global_x, global_y, global_z)
        self.toprightwire = Wire(mid_width / 2.0, 0.0, height,
                                 top_width / 2.0, 0.0, wire_spacing + height,
                                 self.wire_radius_m)
        self.toprightwire.translate(global_x, global_y, global_z)
        self.middlewire = Wire(-mid_width / 2.0, 0.0, height,
                               mid_width / 2.0, 0.0, height, self.wire_radius_m)
        self.middlewire.translate(global_x, global_y, global_z)
        self.bottomleftwire = Wire(-mid_width / 2.0, 0.0, height,
                                   -top_width / 2.0, 0.0, -wire_spacing + height,
                                   self.wire_radius_m)
        self.bottomleftwire.translate(global_x, global_y, global_z)
        self.bottomwire = Wire(-top_width / 2.0, 0.0, -wire_spacing + height,
                               top_width / 2.0, 0.0, -wire_spacing + height, self.wire_radius_m)
        self.bottomwire.translate(global_x, global_y, global_z)
        self.bottomrightwire = Wire(mid_width / 2.0, 0.0, height,
                                    top_width / 2.0, 0.0, -wire_spacing + height,
                                    self.wire_radius_m)
        self.bottomrightwire.translate(global_x, global_y, global_z)

        mid_segment = self.topwire.get_mid_segment()
        wire_num = self.topwire.get_wire_number()
        self.topload = Load(wire_num, mid_segment, mid_segment)
        print(self.topload)
        mid_segment = self.bottomwire.get_mid_segment()
        wire_num = self.bottomwire.get_wire_number()
        self.bottomload = Load(wire_num, mid_segment, mid_segment)
        print(self.bottomload)
        wire_num = self.middlewire.get_wire_number()
        mid_segment = self.middlewire.get_mid_segment()
        self.excitation = Source(wire_num, mid_segment, current_real, current_imag)

    def repr_geometry(self):
        """
        :return: A NEC string representation of the geometry of the TTFD for simulation
        """
        value = "{}\n{}\n{}\n{}\n{}\n{}\n{}\n".format(self.topleftwire, self.topwire,
                                                      self.toprightwire, self.middlewire,
                                                      self.bottomleftwire, self.bottomwire,
                                                      self.bottomrightwire)
        return value.replace('\n', '\r\n')

    def repr_loads(self):
        """
        :return: A NEC string representation of the loads for the TTFD array
        """
        return "{}\r\n{}\r\n".format(self.topload, self.bottomload)

    def repr_excitations(self):
        """
        :return: A NEC string representation of the excitations for the TTFD array
        """
        return "{}\r\n".format(self.excitation)

    def repr_transmissionlines(self):
        """
        :return: A NEC string representation of the transmission lines for the TTFD array
        """
        return ""

    def repr_comment_string(self):
        """
        :return: A human readable NEC comment string describing some characteristics of the TTFD
        """
        return "{}\r\n".format(self.comment_string)


def get_mm_radius_from_awg(awg):
    """
    Takes in a wire gauge in AWG (American Wire Gauge) and returns the radius in mm. Only works
    for gauges between 0 and 36 inclusive.
    :param awg: American Wire Gauge of to translate into radius mm
    :return: radius of a wire that has the gauge given by AWG
    :raises ValueError: On awg out of bounds
    """
    if awg < 0 or awg > 36:
        raise ValueError("Supplied AWG of {} is invalid".format(awg))
    return 0.127 * math.pow(92, float((36 - awg)) / float(39))


def create_wire_conductivity(tag_number, start_segment_number=0, end_segment_number=0,
                             conductivity=copper_conductivity):
    """
    Applies a NEC compatible conductivity to a given tag number and set of segments with given
    conductivity. If start_segment_number and end_segment_number are blank or 0, then the
    conductivity applies to all segments of the tag_number
    :param tag_number: Which wire number does the conductivity apply to?
    :param start_segment_number: Which start segment in a group to apply the conductivity to
    :param end_segment_number: Which end segment in a group to apply the conductivity to
    :param conductivity: The conductivity in mho's per meter for the wire. Default: copper at 20C
    :return: A NEC compatible LD string
    """
    return "LD 5 {} {} {} {}\r\n".format(tag_number, start_segment_number,
                                         end_segment_number, conductivity)


def create_main_array(num_antennas, antenna_spacing_m, antenna_magnitudes, antenna_phases,
                      log_periodics=False):
    """
    Create the main array of a SuperDARN array, returning the antenna objects
    :param num_antennas: How many antennas in the main array? Typically 16
    :param antenna_spacing_m: How much distance between the antennas in meters? Typically 15.24m
    :param antenna_magnitudes: Magnitude for the sources for each antenna in a python list
    :param antenna_phases: Phase for the sources for each antenna in a python list
    :param log_periodics: Use log periodic antennas instead of TTFD antennas. Default False
    :return: antenna objects describing the main array
    """
    if len(antenna_magnitudes) != num_antennas:
        raise ValueError("Magnitudes array len {} != num_antennas".format(antenna_magnitudes))
    if len(antenna_phases) != num_antennas:
        raise ValueError("Phases array len {} != num_antennas".format(len(antenna_phases)))

    antenna_objects = []
    array_length_m = (num_antennas - 1) * antenna_spacing_m
    for antenna in range(0, num_antennas):
        phase = antenna_phases[antenna]
        magnitude = antenna_magnitudes[antenna]
        real_cur = magnitude * math.cos(phase * math.pi / 180.0)
        imag_cur = magnitude * math.sin(phase * math.pi / 180.0)
        print("Main antenna {} with mag {} and phase {} deg".format(antenna, magnitude, phase))
        x_position = antenna * antenna_spacing_m - array_length_m / 2.0
        if log_periodics:
            antenna_objects.append(LogPeriodic(global_x=x_position, current_real=real_cur,
                                               current_imag=imag_cur))
        else:
            antenna_objects.append(TTFD(global_x=x_position,
                                        current_real=real_cur, current_imag=imag_cur))
    return antenna_objects


def create_int_array(num_antennas, antenna_spacing_m, int_x_spacing_m, int_y_spacing_m,
                     int_z_spacing_m, antenna_magnitudes, antenna_phases, log_periodics=False):
    """
    Create the interferometer array of a SuperDARN array, returning the antenna objects
    :param num_antennas: How many antennas in the interferometer array? Typically 4
    :param antenna_spacing_m: How much distance between the antennas in meters? Typically 15.24m
    :param int_x_spacing_m: How much x distance between the interferometer and the main arrays in m
    :param int_y_spacing_m: How much y distance between the interferometer and the main arrays in m
    :param int_z_spacing_m: How much z distance between the interferometer and the main arrays in m
    :param antenna_magnitudes: Magnitude for the sources for each antenna in a python list
    :param antenna_phases: Phase for the sources for each antenna in a python list
    :param log_periodics: Use log periodic antennas instead of TTFD antennas. Default False
    :return: antenna objects describing the interferometer array
    """
    if len(antenna_magnitudes) != num_antennas:
        raise ValueError("Magnitudes array len {} != num_antennas".format(antenna_magnitudes))
    if len(antenna_phases) != num_antennas:
        raise ValueError("Phases array len {} != num_antennas".format(len(antenna_phases)))

    antenna_objects = []
    array_length_m = (num_antennas - 1) * antenna_spacing_m
    for antenna in range(0, num_antennas):
        phase = antenna_phases[antenna]
        magnitude = antenna_magnitudes[antenna]
        real_cur = magnitude * math.cos(phase * math.pi / 180.0)
        imag_cur = magnitude * math.sin(phase * math.pi / 180.0)
        print("Int antenna {} with mag {} and phase {} deg".format(antenna, magnitude, phase))
        x_position = antenna * antenna_spacing_m - array_length_m / 2.0
        global_x_position = float(x_position) + float(int_x_spacing_m)
        if log_periodics:
            antenna_objects.append(LogPeriodic(global_x=global_x_position, global_y=int_y_spacing_m,
                                               global_z=int_z_spacing_m, current_real=real_cur,
                                               current_imag=imag_cur))
        else:
            antenna_objects.append(TTFD(global_x=global_x_position, global_y=int_y_spacing_m,
                                        global_z=int_z_spacing_m, current_imag=imag_cur,
                                        current_real=real_cur))
    return antenna_objects


def end_geometry(ground_plane_value=1):
    """
    :param ground_plane_value: See NEC user manual, default 1 indicates there is a ground plane
    :return: NEC compatible string that signals end of geometry lines (like GW, GM, etc...)
    """
    if ground_plane_value is not 0:
        return "GE {}\r\n".format(ground_plane_value)


def calculate_angle_from_beam(beam_number, beam_separation=3.24, number_of_beams=16):
    """
    Returns azimuth angle in degrees for a SuperDARN array. Negative values mean CCW of boresite.
    ** Note that this function takes beams indexed from 1 **
    :param beam_number: What beam number to calculate angle for? Typically 1-16
    :param beam_separation: The separation in degrees between beams. Typically 3.24 degrees
    :param number_of_beams: How many beams does this radar have? Typically 16
    :return: The azimuth angle in degrees corresponding to the beam given
    """
    return (beam_number - number_of_beams / 2.0 + 0.5) * beam_separation


def calculate_phase_from_beam(beam_number, frequency_hz, antenna_spacing_m):
    """
    Calculate the necessary phase difference between antennas given beam number, frequency and
    antenna spacing
    :param beam_number: What beam number to calculate angle for? Typically 1-16
    :param frequency_hz: What is the frequency used in Hz?
    :param antenna_spacing_m: What is the straight line antenna spacing in meters?
    :return: phase angle in degrees
    """
    wavelength_m = speed_of_light / float(frequency_hz)
    print("Freq: {:.3f} kHz, Wavelength: {:.2f} m".format(frequency_hz / 1000.0, wavelength_m))
    beam_azimuth = calculate_angle_from_beam(beam_number)
    return 360.0 * antenna_spacing_m * math.sin(beam_azimuth * math.pi / 180.0) / wavelength_m


def calculate_parabolic_phase(frequency_hz, antenna_spacing_m, num_antennas):
    """
    Calculate parabolic phase for antenna array
    :param frequency_hz: What is the frequency used in Hz?
    :param antenna_spacing_m: What is the straight line antenna spacing in meters?
    :param num_antennas: How many antennas to calculate phases for?
    :return: The list of phase delays for each antenna
    """
    raise NotImplementedError("Parabolic phase not implemented yet")


# TODO: Doesn't seem to be working properly... need to debug
def calculate_broadened_phase(frequency_hz, antenna_spacing_m, num_antennas, num_sub_arrays=4):
    """
    Calculate a broadened beam array of phases for the antennas. The resulting beam will be
    broadened by a factor of (num_sub_arrays)^2. See "Beam Broadening for Phased Antenna Arrays
    using Multi-beam Subarrays" by Sridhar Rajagopal - Dallas Technology Lab. via IEEE explore.
    :param frequency_hz: Frequency in Hz
    :param antenna_spacing_m: Antenna spacing in meters
    :param num_antennas: How many antennas in the array
    :param num_sub_arrays: How many sub-arrays to use
    :return: Array containing appropriate phases for a broadened beam.
    """
    sub_array_azimuths = []
    # Calculate optimal sub-array beam directions
    # for m in range(-num_sub_arrays/2, num_sub_arrays/2):
    for m in range(0, num_sub_arrays / 2):
        wavelength_m = speed_of_light / float(frequency_hz)
        # sub_array_azimuths.append(math.acos(m*wavelength_m/(8.0 * antenna_spacing_m)))
        acos_arg = (2 * m + 1) * wavelength_m * num_sub_arrays / (2 * num_antennas * antenna_spacing_m)
        print(m, acos_arg)
        sub_array_azimuths.append(math.acos(acos_arg) - math.pi / 2.0)
        # sub_array_azimuths.append(-math.acos(m * wavelength_m / (8.0 * antenna_spacing_m)))
    # k = 2pi/lambda
    # d = antenna array spacing
    # M is number of subarrays
    # N is total elements
    # Ns is # elements per subarray = N/M
    #  acos[+/-(2m + 1) * pi / kdNs] => acos[+/- (2m+1) * lambda * M/ 2*d*N]
    print("Sub array azimuth values\n{}".format(sub_array_azimuths))
    print("Sub array azimuth values degrees\n{}".format([(x * 180.0 / math.pi) for x in sub_array_azimuths]))

    # Calculate the phases of each sub-array
    element_phases = []
    elements_per_sub_array = num_antennas / num_sub_arrays
    for m in range(0, num_sub_arrays / 2):
        prev_phase = 0
        temp_phase = 360.0 * antenna_spacing_m * math.sin(sub_array_azimuths[m]) / wavelength_m
        for n in range(0, elements_per_sub_array):
            element_phases.append(temp_phase + prev_phase)
            prev_phase = element_phases[-1]
    element_phases += list(reversed(element_phases))
    print("Element phases:\n{}".format(element_phases))
    return element_phases


def calculate_circular_phase(frequency_hz, antenna_spacing_m, num_antennas):
    """
    Calculate circular phase for antenna array
    :param frequency_hz: What is the frequency used in Hz?
    :param antenna_spacing_m: What is the straight line antenna spacing in meters?
    :param num_antennas: How many antennas to calculate phases for?
    :return: The list of phase delays for each antenna
    """
    # TODO: Complete this method
    raise NotImplementedError("Circular phase not implemented")


def frequency_card(num_freq_steps=1, start_frequency=8.0, freq_step_size=0.5):
    """
    :param num_freq_steps: How many frequency steps to calculate output for, default 1
    :param start_frequency: What is the starting frequency in MHz? Default 8
    :param freq_step_size: What is the frequency step size in MHz? Default 0.5
    :return: NEC compatible frequency calculation card
    """
    return "FR 0 {} 0 0 {} {}\r\n".format(num_freq_steps, start_frequency, freq_step_size)


def radiation_pattern_card(theta_start=45.0, theta_increment=0.0, theta_steps=1,
                           phi_start=0.0, phi_increment=1.0, phi_steps=361):
    """
    :param theta_start: Start elevation angle in degrees. Default 45.0
    :param theta_increment: Elevation increment angle in degrees. Default 0.0
    :param theta_steps: How many steps in elevation to calculate. Default 1
    :param phi_start: Start azimuth angle in degrees. Default 0.0
    :param phi_increment: Azimuth increment angle in degrees. Default 1.0
    :param phi_steps: How many steps in azimuth to calculate. Default 361
    :return: NEC compatible radiation pattern calculation card.
    """
    return "RP 0 {} {} 1000 {} {} {} {}\r\n".format(theta_steps, phi_steps, theta_start,
                                                    phi_start, theta_increment, phi_increment)


def ground_card(ground_type=2, epse=13, conductivity=0.005):
    """
    :param ground_type: See NEC user manual. 2 is Sommerfeld ground. 0 finite gnd, 1 perfect gnd
    :param epse: See NEC user manual. 13 is relative dielectric constant for gnd in vicinity
    :param conductivity: Conductivity in mhos/meter in the case of perfect ground
    :return: The ground card NEC compatible string
    """
    return "GN {} 0 0 0 {} {}\r\n".format(ground_type, epse, conductivity)


def extended_kernel_card():
    """
    :return: The extended kernel card NEC compatible string
    """
    return "EK\r\n"


def end_of_run_card():
    """
    :return: The end of run card NEC compatible string
    """
    return "EN"


def max_coupling_card():
    """
    :return: The max coupling card NEC compatible string
    """
    return "CP * * * *\r\n"


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--antennas", help="How many antennas in the main array?",
                        default=16, type=int)
    parser.add_argument("-i", "--int_antennas",
                        help="How many antennas in the interferometer array?",
                        default=4, type=int)
    parser.add_argument("-w", "--power",
                        help="How much power is output per antenna? (Watts)",
                        default=500.0, type=float)
    parser.add_argument("-P", "--phase",
                        help="How much phase difference is there between antennas? (degrees)",
                        default=0.0, type=float)
    parser.add_argument("-p", "--parabolic_phase", help="Use a parabolic phase distribution",
                        action="store_true")
    parser.add_argument("-c", "--circular_phase", help="Use a circular phase distribution",
                        action="store_true")
    parser.add_argument("-B", "--broadened_beam", help="Use a broadened beam phase distribution",
                        action="store_true")
    parser.add_argument("-b", "--beam", help="Which beam to transmit on?", default=0, type=float)
    parser.add_argument("-f", "--frequency", help="What frequency to transmit on? MHz", default=10.5)
    parser.add_argument("-F", "--without_fence", help="Generate the array without fence",
                        action="store_true")
    parser.add_argument("-s", "--antenna_spacing",
                        help="What is the spacing between antennas? (m)",
                        default=15.24, type=float)
    parser.add_argument("-x", "--int_x_spacing",
                        help="The x spacing between main and int arrays? (m)",
                        default=0.0, type=float)
    parser.add_argument("-y", "--int_y_spacing",
                        help="The y spacing between main and int arrays? (m)",
                        default=-100.0, type=float)
    parser.add_argument("-z", "--int_z_spacing",
                        help="The z spacing between main and int arrays? (m)",
                        default=0.0, type=float)
    parser.add_argument("-o", "--output_file", help="Generate named output file",
                        default="superdarn_array_output.nec")
    parser.add_argument("-l", "--log_periodic", help="Use log periodics instead of TTFD antennas",
                        action="store_true")
    args = parser.parse_args()

    if args.output_file is not None:
        print("Outputting data to {}".format(args.output_file))

    if args.beam is not 0:
        rel_phase = calculate_phase_from_beam(args.beam, args.frequency * 1e6, args.antenna_spacing)
    else:
        rel_phase = 0
    antenna_magnitudes = []
    antenna_phases = []
    int_antenna_magnitudes = []
    int_antenna_phases = []

    if args.circular_phase:
        antenna_phases = calculate_circular_phase(args.frequency * 1e6, args.antenna_spacing,
                                                  args.antennas)
        int_antenna_phases = calculate_circular_phase(args.frequency * 1e6, args.antenna_spacing,
                                                      args.int_antennas)
    elif args.parabolic_phase:
        antenna_phases = calculate_parabolic_phase(args.frequency * 1e6, args.antenna_spacing,
                                                   args.antennas)
        int_antenna_phases = calculate_parabolic_phase(args.frequency * 1e6, args.antenna_spacing,
                                                       args.int_antennas)
    elif args.broadened_beam:
        antenna_phases = calculate_broadened_phase(args.frequency * 1e6, args.antenna_spacing,
                                                   args.antennas, num_sub_arrays=4)
        int_antenna_phases = calculate_broadened_phase(args.frequency * 1e6, args.antenna_spacing,
                                                       args.int_antennas, num_sub_arrays=2)
        for m_ant in range(0, args.antennas):
            # if m_ant > 3 and m_ant < 8:
            antenna_magnitudes.append(1)
            # else:
            #    antenna_magnitudes.append(0)

        for i_ant in range(0, args.int_antennas):
            int_antenna_magnitudes.append(0)

    else:
        for m_ant in range(0, args.antennas):
            phase = rel_phase * m_ant
            antenna_magnitudes.append(1)
            antenna_phases.append(phase)

        for i_ant in range(0, args.int_antennas):
            phase = rel_phase * i_ant
            int_antenna_magnitudes.append(0)
            int_antenna_phases.append(phase)

    with open(args.output_file, 'w') as f:
        main_antenna_objects = create_main_array(args.antennas, args.antenna_spacing,
                                                 antenna_magnitudes, antenna_phases,
                                                 log_periodics=args.log_periodic)
        for m_ant in main_antenna_objects:
            f.write(m_ant.repr_geometry())
        if args.int_antennas > 0:
            int_antenna_objects = create_int_array(args.int_antennas, args.antenna_spacing,
                                                   args.int_x_spacing, args.int_y_spacing,
                                                   args.int_z_spacing, int_antenna_magnitudes,
                                                   int_antenna_phases, log_periodics=args.log_periodic)
            for i_ant in int_antenna_objects:
                f.write(i_ant.repr_geometry())
        if not args.without_fence:
            reflector_length = (args.antennas + 1) * args.antenna_spacing
            reflector_spacing = 0.707
            f.write(str(Reflector(reflector_length, reflector_spacing, num_wires=21)))
            if args.int_antennas > 0:
                int_reflector_length = (args.int_antennas + 1) * args.antenna_spacing
                int_reflector_spacing = 0.707
                f.write(str(Reflector(int_reflector_length, int_reflector_spacing,
                                      global_x=args.int_x_spacing, global_y=args.int_y_spacing,
                                      global_z=args.int_z_spacing, num_wires=21)))
        f.write(end_geometry())
        for wire in range(0, wire_number):
            if args.log_periodic:
                f.write(create_wire_conductivity(wire, conductivity=aluminum_conductivity))
            else:
                f.write(create_wire_conductivity(wire))
        for m_ant in main_antenna_objects:
            f.write(m_ant.repr_loads())
        if args.int_antennas > 0:
            for i_ant in int_antenna_objects:
                f.write(i_ant.repr_loads())
        f.write(ground_card())
        f.write(extended_kernel_card())
        f.write(max_coupling_card())
        for m_ant in main_antenna_objects:
            f.write(m_ant.repr_excitations())
            f.write(m_ant.repr_transmissionlines())
            f.write(m_ant.repr_comment_string())
        if args.int_antennas > 0:
            for i_ant in int_antenna_objects:
                f.write(i_ant.repr_excitations())
                f.write(i_ant.repr_transmissionlines())
        f.write(frequency_card(start_frequency=args.frequency))
        f.write(radiation_pattern_card(theta_start=0, theta_increment=1, theta_steps=90))
        f.write(end_of_run_card())

    sys.exit()
