import numpy as np


BINS = [2, 4, 8, 16, 32, 64, 128, 256, 384, 512, 640, 768, 896, 1024]


def prepare_samples(data):
    samples = np.frombuffer(data, dtype=np.uint32)
    transformed_samples = np.fft.fft(samples)
    binned_samples = []
    for lower, upper in zip(BINS[:-1], BINS[1:]):
        binned_samples.append(
            np.sum(np.square(np.absolute(transformed_samples[lower:upper])))
        )
    return binned_samples
