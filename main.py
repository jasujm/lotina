import gc
import machine
import time

gc.enable()

TOPIC_SAMPLES = b"/lotina/audio/samples"
TOPIC_PREDICTION = b"/lotina/audio/prediction"

STATE_IDLE = 0
STATE_PRE_RINSE = 1
STATE_SOAP = 2
STATE_POST_RINSE = 3


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
    def __init__(self):
        self._signal_ping = machine.Pin(25, machine.Pin.OUT)
        self._predictions = []
        self._timestamp = time.time()
        self._transit_to_idle()

    def _transit_to_pre_rinse(self):
        self._state = STATE_PRE_RINSE
        self._signal_ping.value(0)

    def _transit_to_soap(self):
        print("soap time...")
        self._state = STATE_SOAP
        self._timestamp = time.time()
        # TODO: 🎵 here goes music 🎵
        self._signal_ping.value(1)
        time.sleep(20)

    def _transit_to_post_rinse(self):
        print("rinse time...")
        self._state = STATE_POST_RINSE
        self._timestamp = time.time()
        self._signal_ping.value(0)

    def _transit_to_idle(self):
        self._state = STATE_IDLE
        self._signal_ping.value(0)

    def handle_tick(self):
        if self._state == STATE_IDLE:
            if sum(prediction > 127 for prediction in self._predictions) >= 2:
                self._transit_to_pre_rinse()
        elif self._state == STATE_PRE_RINSE:
            if sum(prediction > 127 for prediction in self._predictions) < 2:
                self._transit_to_soap()
        elif self._state == STATE_SOAP:
            if time.time() - self._timestamp >= 20:
                self._transit_to_post_rinse()
        elif self._state == STATE_POST_RINSE:
            if time.time() - self._timestamp >= 20:
                self._transit_to_idle()

    def handle_msg(self, topic, msg):
        if topic != TOPIC_PREDICTION:
            return

        prediction = int.from_bytes(msg, "little")
        self._predictions.append(prediction)
        if len(self._predictions) > 5:
            self._predictions.pop(0)


def process_messages(mqtt_broker, mqtt_user, mqtt_passwd):
    from umqtt.simple import MQTTClient
    import time
    import ubinascii

    sck_pin = machine.Pin(14)
    ws_pin = machine.Pin(13)
    sd_pin = machine.Pin(12)
    audio_in = machine.I2S(
        0,
        sck=sck_pin,
        ws=ws_pin,
        sd=sd_pin,
        mode=machine.I2S.RX,
        bits=32,
        format=machine.I2S.MONO,
        rate=22050,
        ibuf=8192,
    )
    samples = bytearray(8192)

    engine = LotinaEngine()

    client_id = ubinascii.hexlify(machine.unique_id())
    client = MQTTClient(client_id, mqtt_broker, user=mqtt_user, password=mqtt_passwd)
    client.set_callback(engine.handle_msg)
    client.connect()
    client.subscribe(TOPIC_PREDICTION)

    while True:
        audio_in.readinto(samples)
        client.publish(TOPIC_SAMPLES, samples)
        time.sleep_ms(500)
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
