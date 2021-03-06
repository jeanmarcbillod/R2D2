"""
generate_KineFold_pairs.py
Parses through KineFold's .rnm output and generates .pair files for
plotting.

--KineFold_dir		= Directory containing KineFold's .rnm output
--outdir		= Output directory

Author: Angela M Yu, 2014-2017
Version: 0.0.1

Copyright (C) 2017  Julius B. Lucks, Angela M Yu.
All rights reserved.
Distributed under the terms of the GNU General Public License, see 'LICENSE'.
"""

from __future__ import division  # allows division of ints to output decimals
import LucksLabUtils_config
import OSU
import SU
import glob
import re
import numpy
from collections import defaultdict

LucksLabUtils_config.config("Quest_R2D2")  # set up environment

# parse command line arguments
opts = OSU.getopts("", ["KineFold_dir=", "out_dir=", "time_weight", "simulation_time_ms=", "last_structure"])
print opts
KineFold_dir = opts["--KineFold_dir"]
outdir = OSU.create_directory(opts["--out_dir"])
time_weight = True if "--time_weight" in opts else False
last_structure = True if "--last_structure" in opts else False
simulation_time_ms = int(opts["--simulation_time_ms"]) if "--simulation_time_ms" in opts else -1

assert int(time_weight) + int(last_structure) <= 1, ("Only can specify either time_weight OR last_structure")


# From Paul Gasper's pairs_from_dbn_2.py
def read_dbn(dbn_fn):
    '''Reads dbn file, returns primary sequence and dot-bracket secondary
       sequence as strings'''
    with open(dbn_fn, 'r') as dbn_fh:
        _ = dbn_fh.next()
        primary_seq = dbn_fh.next().strip()
        secondary_seq = dbn_fh.next().strip()
    return primary_seq, secondary_seq


# From Paul Gasper's pairs_from_dbn_2.py
def dbn_to_pairs(dbn_str):
    ''' Return a pairwise array of base pairs from a .dbn string '''
    #print len(dbn_str)
    bp_array = numpy.zeros([len(dbn_str),len(dbn_str)])
    open_list = []  # open brackets waiting for closing pair
    for char_idx, char in enumerate(dbn_str):
        if char == '.':
            pass
        elif char == '(':
            open_list.append(char_idx)
        elif char == ')':
            bp_array[open_list.pop(), char_idx] = 1
        else:
            raise UserWarning(''' Unrecognized character in secondary 
                                  sequence ''')
    if len(open_list) != 0:
        raise UserWarning(''' Number of open parentheses does not match '''
                          ''' number of closed parentheses in secondary '''
                          ''' structure {0}'''.format(dbn_str))
    return bp_array


# parse *rnm files and create .pair file
rnm_files = glob.glob(KineFold_dir + "/*.rnm")
pair_dict = defaultdict(list)
seq_dict = {}
time_dict = defaultdict(list)
for rf in rnm_files:
    # parse *rnm file for base pairs
    if time_weight:
        kf_dbns, kf_energy_path, kf_times = SU.get_rnm_structs_dbn(rf, outdir, time_weight, simulation_time_ms)
    else:
        kf_dbns, kf_energy_path = SU.get_rnm_structs_dbn(rf, outdir)
    if last_structure:  # ignoring time spent because only considering structure at end of simulation
        OSU.remove_files(kf_dbns[:-1])
        kf_dbns = kf_dbns[-1:]
        kf_energy_path = kf_energy_path[-1:]
    for i in range(len(kf_dbns)):
        seq, struct = read_dbn(kf_dbns[i])
        nt_length = len(seq)
        pairs = dbn_to_pairs(struct)
        pair_dict[nt_length].append(pairs)
        seq_dict[nt_length] = seq
        OSU.remove_file(kf_dbns[i])
        if time_weight:
            time_dict[nt_length].append(kf_times[i])

# Edited from Paul Gasper's pairs_from_dbn_2.py
for key in seq_dict.keys():
    with open('{0}/{1}nt.pairs'.format(outdir, key), 'w') as out_fh:
        out_fh.write('{0}\n'.format(seq_dict[key]))
        if time_weight:
            weighted_bp_array = [(pdk.T * tdk).T for pdk, tdk in zip(pair_dict[key], time_dict[key])]
            avg_bp_array = sum(weighted_bp_array) / sum(time_dict[key])
        else:
            avg_bp_array = sum(pair_dict[key]) / len(pair_dict[key])
        for nt_i in range(avg_bp_array.shape[0]):
            for nt_j in range(avg_bp_array.shape[1]):
                if avg_bp_array[nt_i][nt_j]:
                    out_fh.write('{0}\t{1}\t{2:4.3f}\n'.format(nt_i + 1,
                                                               nt_j + 1,
                                                     avg_bp_array[nt_i][nt_j]))
