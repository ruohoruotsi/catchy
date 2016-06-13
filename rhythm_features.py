
from __future__ import division, print_function

import os
import numpy as np
from bisect import bisect

import utils


onsets_dir = ''
beats_dir = ''


def compute_and_write(data_dir, track_list=None, features=None):
    """Compute frame-based features for all audio files in a folder.

    Args:
        data_dir (str): where to write features
        track_list (str or None): list of file ids. Set to None to infer from
            files in beats_dir and onsets_dir.
        features (dict): dictionary with (unique) feature names as keys and 
            tuples as values, each containing a feature extraction function and a
            parameter dictionary.
            Feature extraction functions can be any function that returns one
                or more 1d or 2d-arrays that share their first dimension.

    Required global variables:
        beats_dir (str): where to find beat data
        onsets_dir (str): where to find onset data
    """
    if track_list is None:
        onsets_ids = [filename.split('.')[0] for filename in os.listdir(onsets_dir)]
        beats_ids = [filename.split('.')[0] for filename in os.listdir(beats_dir)]

        track_list = list(set(onsets_ids + beats_ids))

    if features is None:
        features = {'tempo': (local_tempo, {}),
                    'ioi': (log_ioi, {}),
                    'ioihist': (ioi_histogram, {'min_length': -3, 'max_length': 3, 'step': 0.5})}

    for track_id in track_list:

        print("Computing features for track {}...".format(track_id))

        for feature in features:

            # run feature function
            func, params = features[feature]
            X = func(track_id, **params)

            # flatten
            X = X.flatten()

            # write
            utils.write_feature(X, [data_dir, feature, track_id])


def ioi_histogram(track_id, min_length = -3, max_length = 3, step=0.5):
    """Compute a IOI histogram, with bins logarithmically spaced between
        `min_length` (def: -3) and `max_length` (3), with step `step` (0.5).
    """
    ioi = log_ioi(track_id)

    halfstep = step / 2.0
    nbins = (max_length - min_length) / step + 1
    binedges = np.linspace(min_length - halfstep, max_length + halfstep, nbins + 1)

    ioi_hist, _ = np.histogram(ioi, binedges)
    ioi_hist = ioi_hist / np.sum(ioi_hist)

    return ioi_hist


def log_ioi(track_id):
    """Read beat and IOI data and return the log of the IOI
        normalized by beat length.
    """
    ioi = normalized_ioi(track_id)
    
    return np.array(np.log2(ioi))


def normalized_ioi(track_id):
    """Read beat and IOI data and return IOI normalized by
        beat length.
    """
    beat_times, beat_intervals = get_beats(track_id)
    onset_times, onset_intervals = get_onsets(track_id)

    # prepend a beat at t=0
    if not beat_times[0] == 0:
        np.insert(beat_times, 0, 0)
        np.insert(beat_intervals, 0, beat_times[0])

    norm_ioi = []
    for t, ioi in zip(onset_times, onset_intervals):
        i = bisect(beat_times, t) - 1  # find in sorted list
        norm_ioi.append(ioi / beat_intervals[i])

    return norm_ioi 


def local_tempo(track_id):
    """ Read beat intervals and convert to local tempo
        (LT = 60/BI)
    """
    _, beat_intervals = get_beats(track_id)
    return 60 / beat_intervals


def get_beats(track_id):
    """Read beat data from file beats_dir + track_id + '.csv'.
    File should contain a time column followed by one column of
        beat intervals.
    """
    beats_file = os.path.join(beats_dir, track_id + '.csv')
    t, beat_intervals = utils.read_feature(beats_file, time=True)
    return t, beat_intervals


def get_onsets(track_id):
    """Read ioi data from file onsets_dir + track_id + '.csv'.
    File should contain a time column followed by one column of
        inter-onset intervals.
    """
    onsets_file = os.path.join(onsets_dir, track_id + '.csv')
    t, ioi = utils.read_feature(onsets_file, time=True)
    return t, ioi