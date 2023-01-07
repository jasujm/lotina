# Lotina: The machine learning powered musical soap box

Musical soap box is a soap dispenser that plays music while you’re rubbing soap
to your hands.

Musical soap boxes are typically integrated to the soap dispenser itself,
activating when the soap is dispensed. **Lotina** (Finnish for *squelch*) is not
a soap box. It’s a separate device that records sounds and recognized when tap
is first opened and then closed. After closing the tap and taking soap, it
starts playing music until it’s time to rinse again.

Hence the product description: a musical soap box powered by machine learning.

## Usage

Well, as it stands now, lotina is more a collection of Python utilities than a
software package with well defined installation and usage flow. You can start
by installing the dependencies, then uploading the application to ESP32
(assuming the ESP32 is already flashed with
[micropython](https://micropython.org/)):

```
$ poetry install
$ poetry run ampy --port /dev/ttyUSB0 put main.py
$ poetry run ampy --port /dev/ttyUSB0 put lotina.conf
```

Lotina communicates via MQTT, sending samples and receiving predictions from the
ML model. Use the utilities to record audio samples of tap and other sounds, and
train the model:

```
$ poetry run python -m processor --label tap      # record samples from tsp
$ poetry run python -m processor --label ambiend  # record ambient sound, etc...
$ poetry run python -m modeltraining --evaluate --save
$ poetry run python -m processor --classify       # use the saved model
```
