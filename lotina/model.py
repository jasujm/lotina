import numpy as np
import scipy.signal

SAMPLING_FREQ = 22050
N_SEGMENTS = 1024


def get_input_shape():
    return None, N_SEGMENTS // 2


def to_features(data):
    samples = np.frombuffer(data, dtype=np.uint16)
    spectrogram = scipy.signal.stft(samples, SAMPLING_FREQ, nperseg=N_SEGMENTS)[2]
    return np.transpose(np.abs(spectrogram[1:, :]))
