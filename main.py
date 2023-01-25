import gc
import machine
import time

import notes

gc.enable()

TOPIC_SAMPLES = b"/lotina/audio/samples"
TOPIC_PREDICTION = b"/lotina/audio/prediction"

STATE_IDLE = 0
STATE_PRE_RINSE = 1
STATE_SOAP = 2
STATE_POST_RINSE = 3

SCK_PIN_IN = machine.Pin(32)  # audio in BCLK
WS_PIN_IN = machine.Pin(25)  # audio in LRC
SD_PIN_IN = machine.Pin(33)  # audio in Dout
SCK_PIN_OUT = machine.Pin(14)  # audio out BCLK
WS_PIN_OUT = machine.Pin(13)  # audio out LRC
SD_PIN_OUT = machine.Pin(27)  # audio out Din

AUDIO_SAMPLE_RATE = 22050
AUDIO_SAMPLE_BITS = 16
AUDIO_SAMPLE_BUFFER_LENGTH = 8192

TICK_MS = 500

N_PREDICTIONS = 5
DETECTION_THRESHOLD = 127
N_DETECTIONS = 2
RINSE_TIMEOUT_S = 20


def load_config():
    import json

    with open("lotina.conf") as f:
        return json.load(f)


def init_wifi(ssid, passwd):
    import network

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("connecting to wlan...")
        sta_if.active(True)
        sta_if.connect(ssid, passwd)
        while not sta_if.isconnected():
            pass
    print("connected to wlan:", sta_if.ifconfig())


class LotinaEngine:
    def __init__(self, write_audio):
        self._write_audio = write_audio
        self._predictions = []
        self._timestamp = time.time()
        self._transit_to_idle()

    def _transit_to_pre_rinse(self):
        self._state = STATE_PRE_RINSE

    def _transit_to_soap(self):
        print("soap time...")
        self._state = STATE_SOAP
        self._timestamp = time.time()
        notes.play_song(self._write_audio)
        notes.play_song(self._write_audio)

    def _transit_to_post_rinse(self):
        print("rinse time...")
        self._state = STATE_POST_RINSE
        self._timestamp = time.time()

    def _transit_to_idle(self):
        self._state = STATE_IDLE

    def handle_tick(self):
        if self._state == STATE_IDLE:
            if (
                sum(
                    prediction > DETECTION_THRESHOLD for prediction in self._predictions
                )
                >= N_DETECTIONS
            ):
                self._transit_to_pre_rinse()
        elif self._state == STATE_PRE_RINSE:
            if (
                sum(
                    prediction > DETECTION_THRESHOLD for prediction in self._predictions
                )
                < N_DETECTIONS
            ):
                self._transit_to_soap()
        elif self._state == STATE_SOAP:
            if time.time() - self._timestamp >= RINSE_TIMEOUT_S:
                self._transit_to_post_rinse()
        elif self._state == STATE_POST_RINSE:
            if time.time() - self._timestamp >= RINSE_TIMEOUT_S:
                self._transit_to_idle()

    def handle_msg(self, topic, msg):
        if topic != TOPIC_PREDICTION:
            return

        prediction = int.from_bytes(msg, "little")
        self._predictions.append(prediction)
        if len(self._predictions) > N_PREDICTIONS:
            self._predictions.pop(0)


def process_messages(mqtt_broker, mqtt_user, mqtt_passwd):
    from umqtt.simple import MQTTClient
    import time
    import ubinascii

    audio_in = machine.I2S(
        0,
        sck=SCK_PIN_IN,
        ws=WS_PIN_IN,
        sd=SD_PIN_IN,
        mode=machine.I2S.RX,
        bits=AUDIO_SAMPLE_BITS,
        format=machine.I2S.MONO,
        rate=AUDIO_SAMPLE_RATE,
        ibuf=AUDIO_SAMPLE_BUFFER_LENGTH,
    )
    samples = bytearray(AUDIO_SAMPLE_BUFFER_LENGTH)

    audio_out = machine.I2S(
        1,
        sck=SCK_PIN_OUT,
        ws=WS_PIN_OUT,
        sd=SD_PIN_OUT,
        mode=machine.I2S.TX,
        bits=notes.BITS,
        format=machine.I2S.MONO,
        rate=notes.RATE,
        ibuf=20000,
    )

    engine = LotinaEngine(audio_out.write)

    client_id = ubinascii.hexlify(machine.unique_id())
    client = MQTTClient(client_id, mqtt_broker, user=mqtt_user, password=mqtt_passwd)
    client.set_callback(engine.handle_msg)
    client.connect()
    client.subscribe(TOPIC_PREDICTION)

    while True:
        audio_in.readinto(samples)
        client.publish(TOPIC_SAMPLES, samples)
        time.sleep_ms(TICK_MS)
        client.check_msg()
        engine.handle_tick()


def main():
    config = load_config()
    print("connecting to wifi...")
    init_wifi(ssid=config["wlan_ssid"], passwd=config["wlan_passwd"])
    print("starting the processor...")
    process_messages(
        mqtt_broker=config["mqtt_broker"],
        mqtt_user=config["mqtt_user"],
        mqtt_passwd=config["mqtt_passwd"],
    )


main()
