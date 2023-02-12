import http
import machine
import struct

SCK_PIN_OUT = machine.Pin(14)  # audio out BCLK
WS_PIN_OUT = machine.Pin(13)  # audio out LRC
SD_PIN_OUT = machine.Pin(27)  # audio out Din
BUFFER_SIZE = 20000

CONTENT_TYPES = ["audio/wav", "audio/x-wav"]


def _parse_wav_file(infile):
    magic = infile.read(4)
    if magic != b"RIFF":
        raise RuntimeError("not RIFF file")
    infile.read(4)  # ignore file size
    type_ = infile.read(4)
    if type_ != b"WAVE":
        raise RuntimeError("not WAVE file")
    tag = infile.read(4)
    if tag != b"fmt ":
        raise RuntimeError("missing format chunk")
    (fmt_size,) = struct.unpack_from("<L", infile.read(4))
    if fmt_size != 16:
        raise RuntimeError(f"unexpected format chunk size: {fmt_size}")
    fmt_type, n_channels, sample_rate, _, _, bits_per_sample = struct.unpack_from(
        "<HHLLHH", infile.read(16)
    )
    if fmt_type != 1:
        raise RuntimeError(f"unexpected format type: {fmt_type}")
    while True:
        tag = infile.read(4)
        if not tag:
            raise RuntimeError("missing data chunk")
        if tag == b"data":
            break
        (chunk_size,) = struct.unpack_from("<L", infile.read(4))
        infile.read(chunk_size)
    (data_size,) = struct.unpack_from("<L", infile.read(4))
    return n_channels, sample_rate, bits_per_sample, data_size


def _prepare_i2s_bus(n_channels, sample_rate, bits_per_sample):
    return machine.I2S(
        1,
        sck=SCK_PIN_OUT,
        ws=WS_PIN_OUT,
        sd=SD_PIN_OUT,
        mode=machine.I2S.TX,
        bits=bits_per_sample,
        format=machine.I2S.MONO if n_channels == 1 else machine.I2S.STEREO,
        rate=sample_rate,
        ibuf=BUFFER_SIZE,
    )


def play(url):
    infile = http.open_get_request(url, accept=CONTENT_TYPES)
    audio_out = None
    try:
        n_channels, sample_rate, bits_per_sample, data_size = _parse_wav_file(infile)
        audio_out = _prepare_i2s_bus(n_channels, sample_rate, bits_per_sample)
        samples = bytearray(BUFFER_SIZE)
        while data_size > 0:
            n_read = infile.readinto(samples, min(BUFFER_SIZE, data_size))
            data_size -= n_read
            if n_read == 0:
                break
            audio_out.write(samples)
    except Exception as e:
        print(f"error playing tone: {e}")
    finally:
        if audio_out:
            audio_out.deinit()
        infile.close()
