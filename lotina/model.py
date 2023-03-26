import numpy as np
import scipy.signal

SAMPLING_FREQ = 22050
N_SEGMENTS = 1024


def _get_bins(step, bound):
    two_to_step = 2**step
    return [
        *(2**i for i in range(step)),
        *range(two_to_step, 2**bound + 1, two_to_step),
    ]


BINS = _get_bins(5, 10)


def _calculate_signal_whiteness(x, m=10):
    xc = np.correlate(x, x, mode="full")
    return sum(float(xc[i]) ** 2 for i in range(1, m)) / float(xc[0]) ** 2


def extract_features_from_data(data):
    samples = np.frombuffer(data, dtype=np.uint32)
    transformed_samples = np.fft.fft(samples)
    features = []
    sum_of_squares = np.sum(np.square(np.absolute(transformed_samples)))
    for lower, upper in zip(BINS[:-1], BINS[1:]):
        features.append(
            np.sum(np.square(np.absolute(transformed_samples[lower:upper])))
            / sum_of_squares
        )
    features.append(_calculate_signal_whiteness(samples))
    return features


def get_input_shape():
    return None, N_SEGMENTS // 2


def to_features(data):
    samples = np.frombuffer(data, dtype=np.uint16)
    spectrogram = scipy.signal.stft(samples, SAMPLING_FREQ, nperseg=N_SEGMENTS)[2]
    return np.transpose(np.abs(spectrogram[1:, :]))
