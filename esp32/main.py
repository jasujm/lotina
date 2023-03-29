import gc
import machine
import time

import notes

gc.enable()

STATE_IDLE = b"idle"
STATE_WASHING = b"washing"
STATE_SOAP = b"soap"
STATE_COOLDOWN = b"cooldown"

SCK_PIN_IN = machine.Pin(32)  # audio in BCLK
WS_PIN_IN = machine.Pin(25)  # audio in LRC
SD_PIN_IN = machine.Pin(33)  # audio in Dout

MQTT_KEEPALIVE = 120
MQTT_AVAILABILITY_INTERVAL = 60
STATE_ON = b"ON"
STATE_OFF = b"OFF"
STATE_ONLINE = b"online"
STATE_OFFLINE = b"offline"

AUDIO_SAMPLE_RATE = 22050
AUDIO_SAMPLE_BITS = 16
AUDIO_SAMPLE_BUFFER_LENGTH = 16384

DETECTION_THRESHOLD = 127
HAND_WASHING_DETECTED_TIMEOUT_S = 3
HAND_WASHING_OVER_TIMEOUT_S = 20


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
    def __init__(self, song_url, publisher):
        self._publisher = publisher
        self._song_url = song_url
        self._prediction = 0
        self._enabled = True
        self._timestamp = time.time()
        self._state = None

    def start(self):
        client = self._publisher._client
        topic_prefix = self._publisher._topic_prefix
        client.set_callback(self._handle_msg)
        self._publisher.connect()
        client.subscribe(f"{topic_prefix}/prediction".encode())
        client.subscribe(f"{topic_prefix}/enabled".encode())
        client.subscribe(f"{topic_prefix}/set_enabled".encode())
        self._transit_to_idle()

    def _transit_to(self, state):
        print("state:", state)
        self._state = state
        self._publisher.publish_state(state)

    def _transit_to_idle(self):
        self._transit_to(STATE_IDLE)

    def _transit_to_hand_washing_detected(self):
        self._transit_to(STATE_WASHING)
        self._timestamp = time.time()

    def _transit_to_soap(self):
        self._transit_to(STATE_SOAP)
        self._publisher.publish_interrupt()
        notes.play(self._song_url)

    def _transit_to_hand_washing_over(self):
        self._transit_to(STATE_COOLDOWN)
        self._timestamp = time.time()

    def handle_tick(self):
        if not self._enabled:
            return
        if self._state == STATE_IDLE:
            if self._prediction > DETECTION_THRESHOLD:
                self._transit_to_hand_washing_detected()
        elif self._state == STATE_WASHING:
            if time.time() - self._timestamp >= HAND_WASHING_DETECTED_TIMEOUT_S:
                self._transit_to_soap()
        elif self._state == STATE_SOAP:
            if self._prediction < DETECTION_THRESHOLD:
                self._transit_to_hand_washing_over()
        elif self._state == STATE_COOLDOWN:
            if time.time() - self._timestamp >= HAND_WASHING_OVER_TIMEOUT_S:
                self._transit_to_idle()

    def _handle_msg(self, topic, msg):
        if topic.endswith(b"/prediction"):
            try:
                self._prediction = int(msg)
            except ValueError:
                pass
        elif (
            topic.endswith(b"/enabled") or topic.endswith(b"/set_enabled")
        ) and msg in (
            STATE_ON,
            STATE_OFF,
        ):
            self._enabled = bool(msg == STATE_ON)
            print("enabled:", self._enabled)
            self._publisher.publish_enabled(msg.replace(b"/set_enabled", b"/enabled"))
            if not self._enabled:
                self._publisher.publish_interrupt()
                self._transit_to_idle()


class SamplePublisher:
    def __init__(self, topic_prefix, client, sample_publish_threshold):
        self._topic_prefix = topic_prefix
        self._samples_topic = f"{topic_prefix}/samples".encode()
        self._state_topic = f"{topic_prefix}/state".encode()
        self._availability_topic = f"{topic_prefix}/availability".encode()
        self._enabled_topic = f"{topic_prefix}.enabled".encode()
        self._client = client
        self._sample_publish_threshold = sample_publish_threshold
        self._audio_above_threshold_detected = True
        self._last_availability_timestamp = 0

    def connect(self):
        self._client.set_last_will(self._availability_topic, STATE_OFFLINE, retain=True)
        self._client.connect()
        self._client.publish(self._availability_topic, STATE_ONLINE, retain=True)

    def keepalive(self):
        t = time.time()
        if t - self._last_availability_timestamp >= MQTT_AVAILABILITY_INTERVAL:
            self._client.ping()
            self._last_availability_timestamp = t

    def publish_state(self, state):
        self._client.publish(self._state_topic, state, retain=True)

    def publish_enabled(self, enabled):
        self._client.publish(self._enabled_topic, enabled, retain=True)

    def publish_interrupt(self):
        if self._audio_above_threshold_detected:
            self._client.publish(self._samples_topic, b"")
        self._audio_above_threshold_detected = False

    def publish_samples(self, samples):
        _min = _max = int.from_bytes(samples[:2], "little")
        for i in range(2, len(samples), 2):
            sample = int.from_bytes(samples[i : i + 2], "little")
            if sample < _min:
                _min = sample
            elif sample > _max:
                _max = sample
            if _max - _min > self._sample_publish_threshold:
                self._audio_above_threshold_detected = True
                self._client.publish(self._samples_topic, samples)
                return
        self.publish_interrupt()


def process_messages(
    identity, mqtt_broker, mqtt_user, mqtt_passwd, song_url, sample_publish_threshold
):
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

    client_id = ubinascii.hexlify(machine.unique_id())
    client = MQTTClient(
        client_id,
        mqtt_broker,
        user=mqtt_user,
        password=mqtt_passwd,
        keepalive=MQTT_KEEPALIVE,
    )

    topic_prefix = f"lotina/{identity}"
    publisher = SamplePublisher(topic_prefix, client, sample_publish_threshold)

    engine = LotinaEngine(song_url, publisher)
    engine.start()

    while True:
        publisher.keepalive()
        audio_in.readinto(samples)
        publisher.publish_samples(samples)
        client.check_msg()
        # Marking sample_publish_threshold < 0 means we just want to record
        # Do not run the state machine then
        if sample_publish_threshold >= 0:
            engine.handle_tick()


def main():
    config = load_config()
    print("connecting to wifi...")
    init_wifi(ssid=config["wlan_ssid"], passwd=config["wlan_passwd"])
    print("starting the processor...")
    process_messages(
        identity=config["identity"],
        mqtt_broker=config["mqtt_broker"],
        mqtt_user=config["mqtt_user"],
        mqtt_passwd=config["mqtt_passwd"],
        song_url=config["song_url"],
        sample_publish_threshold=config["sample_publish_threshold"],
    )


main()
