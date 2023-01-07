import json
import machine


def load_config():
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


def publish_messages(mqtt_broker, mqtt_user, mqtt_passwd):
    import gc
    from umqtt.simple import MQTTClient
    import time
    import ubinascii

    gc.enable()

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

    client_id = ubinascii.hexlify(machine.unique_id())
    topic_pub = b"/lotina/audio/samples"
    client = MQTTClient(client_id, mqtt_broker, user=mqtt_user, password=mqtt_passwd)
    client.connect()

    while True:
        audio_in.readinto(samples)
        client.publish(topic_pub, samples)
        time.sleep(1)


def main():
    config = load_config()
    print("connecting to wifi...")
    init_wifi(ssid=config["wlan_ssid"], passwd=config["wlan_passwd"])
    print("starting to publish...")
    publish_messages(
        mqtt_broker=config["mqtt_broker"],
        mqtt_user=config["mqtt_user"],
        mqtt_passwd=config["mqtt_passwd"],
    )


main()
