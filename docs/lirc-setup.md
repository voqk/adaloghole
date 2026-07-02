# LIRC + USB-UIRT setup (Phase 1 Actuator)

One-time setup to let the `lirc` Actuator mute the real TV. Until this is done,
leave `actuator = "none"` in `server/adaloghole.toml` — the see→decide loop runs
fine and logs the Commands it *would* fire.

## 1. Install LIRC

```sh
sudo apt install lirc
```

## 2. Plug in the USB-UIRT and point LIRC at it

The USB-UIRT enumerates as an FTDI serial device (check `lsusb` / `dmesg` — it
appears as something like `ttyUSB0`). Edit `/etc/lirc/lirc_options.conf`:

```ini
[lircd]
driver = usb_uirt_raw     # provided by the lirc "usb_uirt" userspace driver
device = /dev/ttyUSB0
```

> If your LIRC build lacks the `usb_uirt_raw` driver, install `lirc-drv-usbuirt`
> (some distros package it separately) or build it from the LIRC source tree.

Restart LIRC and confirm the daemon is happy:

```sh
sudo systemctl restart lircd
sudo systemctl status lircd
```

## 3. Learn the TV's mute code with irrecord

Stop lircd first (irrecord needs exclusive device access), then record. Name
the remote `tv` — that's what `[actuator.lirc] remote` in adaloghole.toml
expects.

```sh
sudo systemctl stop lircd
sudo irrecord --driver usb_uirt_raw --device /dev/ttyUSB0 ~/tv.lircd.conf
```

Follow the prompts; when asked for a key name, use `KEY_MUTE` and press the
real remote's mute button at the receiver. Then install the config and restart:

```sh
sudo cp ~/tv.lircd.conf /etc/lirc/lircd.conf.d/tv.lircd.conf
sudo systemctl start lircd
```

## 4. Smoke-test irsend against the real TV

```sh
irsend LIST tv ""                 # should list KEY_MUTE
irsend SEND_ONCE tv KEY_MUTE      # TV should mute
irsend SEND_ONCE tv KEY_MUTE      # ...and unmute (mute is a toggle on most TVs)
```

Aim the USB-UIRT's emitter at the TV; range is modest, so keep it within a few
meters with line of sight.

## 5. Switch AdalogHole to the lirc actuator

In `server/adaloghole.toml`:

```toml
[roles]
actuator = "lirc"

[actuator.lirc]
remote = "tv"                # the name you gave irrecord

[actuator.lirc.codes]
"tv.mute"   = "KEY_MUTE"     # Command code_ref -> LIRC key name
"tv.unmute" = "KEY_MUTE"     # mute is a toggle key on most TVs
```

Restart the server. A state flip now fires real IR; failures (unplugged device,
lircd down) come back as failed Acks in the log — the loop keeps running.

> **Toggle caveat:** because most TVs expose mute as a single toggle key, the
> TV's true state can drift from the Brain's if someone also uses the physical
> remote. The override knob in `/admin` (force mute / force unmute) is the
> resync tool.

## Later (Phase 2, Raspberry Pi)

The same LIRC actuator works unchanged on a Pi — either plug the USB-UIRT into
the Pi, or switch LIRC's driver to the `gpio-ir` overlay with a bare IR LED.
