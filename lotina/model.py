import numpy as np


def _get_bins(step, bound):
    two_to_step = 2**step
    return [
        *(2**i for i in range(step)),
        *range(two_to_step, 2**bound + 1, two_to_step),
    ]


BINS = _get_bins(6, 10)


def prepare_samples(data):
    samples = np.frombuffer(data, dtype=np.uint32)
    transformed_samples = np.fft.fft(samples)
    binned_samples = []
    sum_of_squares = np.sum(np.square(np.absolute(transformed_samples)))
    for lower, upper in zip(BINS[:-1], BINS[1:]):
        binned_samples.append(
            np.sum(np.square(np.absolute(transformed_samples[lower:upper])))
            / sum_of_squares
        )
    return binned_samples
