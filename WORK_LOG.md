# Work Log

## Wed 19 Aug 2026

### Blog setup

Based on

- [https://github.com/saramic/vape-cell-EV/commit/60733c2ceb1aca705c3f8076d91916f447fb7965](
   https://github.com/saramic/vape-cell-EV/commit/60733c2ceb1aca705c3f8076d91916f447fb7965)


```sh
mise use ruby@3.2.2
gem install jekyll bundler
jekyll new docs

cd docs

# downgrade jekyll to 3.9.5
# gem "jekyll", "~> 3.9.5" # to work with github-pages
bundle add github-pages webrick

# configure the _config.yml

# run
bundle exec jekyll serve --port 8888

# open
http://127.0.0.1:8888/paws-and-wait/
```

### Plan

Drafted the Week 1 plan below from `reference/SUBMISSION.pdf` (Phases 1A–1C) ahead of
hardware arriving. Kit on order: CM5104032 (4GB RAM / 32GB eMMC / Wireless) Dev Kit —
CM5 module, IO Board (pre-fitted in IO Case), Cooler, Antenna Kit, 27W USB-C PD PSU,
2× HDMI-HDMI cables, USB-A→USB-C cable. No Hailo-8L or cameras yet — that's Week 2+.

### Week 1 goal
Get the Dev Kit flashed, booted, networked, headless-accessible, both cameras
streaming simultaneously, and a CPU-only YOLOv8s inference baseline recorded.
This is the "Unboxing post + hardware quality review + camera and baseline CPU
benchmark results" deliverable for Week 1.

### Day 1 — Unbox & flash (Phase 1A.1)
- [ ] Photograph the unboxing (kit contents, board close-ups) for the write-up
- [ ] Inspect CM5 module and IO Board for shipping damage, confirm CM5 is seated
      correctly on the IO Board's high-density connector
- [ ] Fit the cooler + case fan, connect the antenna kit
- [ ] Set the IO Board's boot-mode switch to USB-boot (nRPIBOOT) per the quick-start
      card in the box, connect USB-C from the IO Board to a host machine
- [ ] Flash Raspberry Pi OS (64-bit) to the 32GB eMMC using Raspberry Pi Imager
      (it drives rpiboot automatically once the board enumerates as a mass-storage
      device) — enable SSH + set hostname/user in the Imager's advanced options
      before writing, to skip first-boot setup
- [ ] Flip the boot switch back to eMMC boot, disconnect from the host, connect
      power via the 27W PSU

### Day 2 — First boot & IO sanity check (Phase 1A.2)
- [ ] Boot with HDMI + keyboard attached first to confirm a clean first boot
- [ ] Confirm all IO Board ports functional: HDMI, USB 3.0 (x2), Gigabit
      Ethernet, 40-pin GPIO header present and unbent
- [ ] `sudo raspi-config` — expand filesystem if needed, set locale/timezone
- [ ] Run `vcgencmd measure_temp` and `vcgencmd get_throttled` idle to record a
      baseline (compare later under load in Phase 1C)

### Day 3 — Networking & remote access (Phase 1A.3–1A.4)
- [ ] Connect over Wi-Fi, confirm dual-band (2.4/5GHz) association
- [ ] `iwconfig` / `iw dev wlan0 link` — record signal strength (RSSI) and
      negotiated link rate
- [ ] Enable SSH (`sudo raspi-config` → Interface Options, if not already set at
      flash time) and confirm login from another machine on the LAN
- [ ] Enable VNC, confirm remote desktop access over the local network
- [ ] Note down static IP / mDNS hostname (`raspberrypi.local`) for the rest of
      the road test

### Day 4 — Camera setup, single then dual (Phase 1B.1–1B.2)
- [ ] Connect Camera Module 3 to CSI port 0 (dog station), confirm with
      `libcamera-hello --list-cameras` / `rpicam-hello`
- [ ] Capture a test still and short clip from camera 0
- [ ] Connect Camera Module 3 to CSI port 1 (cat station), confirm both cameras
      enumerate together
- [ ] Run both cameras simultaneously (`rpicam-vid` on each) and confirm no
      resource conflicts

### Day 5 — Camera bandwidth benchmark (Phase 1B.3–1B.4)
- [ ] Measure frame capture latency and CPU usage for dual 1080p streams
      (`rpicam-vid` + `htop` side by side, or `vcgencmd measure_clock`)
- [ ] Confirm both cameras sustain 30fps simultaneously without frame drops —
      log any dropped-frame warnings
- [ ] Record numbers in the benchmark table (see below)

### Day 6 — CPU-only inference baseline (Phase 1C)
- [ ] `pip install ultralytics`, run YOLOv8s object detection on a live camera feed
- [ ] Run for 10 minutes continuously, sustained load
- [ ] Record: FPS, CPU utilisation, RAM usage, CPU temperature, and any thermal
      throttling events (`vcgencmd get_throttled` before/after)
- [ ] Repeat for single camera, then dual camera — this is the number Week 2's
      Hailo-accelerated run gets compared against

### Day 7 — Buffer + write-up
- [ ] Catch up on anything that slipped
- [ ] Draft the Week 1 element14 post: unboxing photos, hardware quality notes,
      camera setup steps, baseline CPU benchmark table

### Benchmark log (fill in as measured)

| Metric | Target/Note | Result |
|---|---|---|
| Wi-Fi signal strength (RSSI) | record | |
| Idle CPU temp | record | |
| Dual 1080p capture latency | record | |
| Dual-camera sustained FPS | 30fps each, no drops | |
| CPU-only YOLOv8s FPS (single cam) | record — this is the Week 2 comparison baseline | |
| CPU-only YOLOv8s FPS (dual cam) | record | |
| CPU utilisation during inference | record | |
| Thermal throttling under 10min sustained load | none expected (case fan fitted) | |

### Notes / blockers
- IO Board's boot mode is a **jumper**, not a switch: full CM5 IO Board
  datasheet confirms **J2 jumper, pins 1–2 (`nRPIBOOT`)** forces USB boot
  instead of eMMC. Flash via the dedicated **USB 2.0 Type-C port** ("primarily
  intended for data transfer and enabling board updates through rpiboot"),
  then remove the jumper and power-cycle normally.
- The IO Board has **no PCIe HAT+ connector** — its "Raspberry Pi HAT connector"
  (section 4.2 of the datasheet) is the plain 40-pin GPIO HAT footprint only.
  PCIe expansion is *only* via the M.2 M-key socket (Gen 2 ×1, 5Gb/s by
  default). This is why the AI HAT+ can't be used as a HAT here — see
  purchasing decisions below.

### Purchasing decisions (revised BOM, cash-conscious)

Original submission BOM (§3.2) revised after checking exact part compatibility
against the CM5 IO Board — full reasoning in chat history, summary below.

**Hailo-8L (AI accelerator):**
- ❌ Raspberry Pi AI HAT+ 13 TOPS (~$124, Core Electronics) — ruled out. The
  Hailo chip is soldered directly to the HAT+ PCB and only reachable via Pi
  5's dedicated PCIe HAT+ ribbon connector, which the CM5 IO Board doesn't have.
  (The older, now-discontinued "AI Kit" had a removable M.2 module — that's
  the one forum posts about CM5 refer to. Not buyable new any more.)
- ✅ **Buy: Mouser HM21LB1C2LAE** — genuine Hailo-8L, M.2 Key **B+M**, size
  2280, 13 TOPS, ~$135 AUD. Bare module, plugs directly into the IO Board's
  M.2 socket. (Also listed at Farnell/element14 UK — worth checking
  element14.com.au for local stock before ordering from Mouser.)
- ❌ Avoid HM21LB1C2KAE — same chip but M.2 Key **A+E** (2230), wrong
  connector shape, won't fit an M-key-only socket.
- ❌ Hailo-8 26 TOPS (~$345) — skip. IO Board only wires Gen 2 ×1 to the M.2
  socket regardless of which module is fitted, so the pricier chip's extra
  bandwidth is wasted, and 13 TOPS already clears the submission's own
  benchmark targets for this workload.
- Driver stack is `sudo apt install hailo-all` (as already planned in Phase
  2A) — generic to any Hailo-8L module, not tied to buying Pi's own HAT+.
  Budget slack for possible kernel/dkms hiccups after a fresh OS install —
  real forum reports exist, usually fixed by updating to current Pi OS/kernel
  before installing, or a clean reinstall + reboot between steps.

**Cameras — switched to Arducam, not Camera Module 3:**
- ✅ **Buy: 2× Arducam 8MP IMX219 Auto Focus (AC-B0393), $35.55 each** —
  chosen over the cheaper Fixed Focus variant (AC-B0390, $13.40) specifically
  for **lead time**: AC-B0390 is 14–18 days out, AC-B0393 ships next-day.
  AC-B0393 also ships with the correct **22-22pin FFC cable** natively (no
  separate adapter needed) — confirmed via package contents listing.
  (AC-B0390 ships with an older Pi Zero-style 22-pin 1.0mm-pitch adapter,
  which does *not* fit the IO Board's 22-pin **0.5mm**-pitch connector — would
  have needed a separate $1.83 CE09775 adapter cable per camera.)
- Lock focus once mounted rather than running true autofocus: use
  `v4l2-ctl -d /dev/v4l-subdev1 -c focus_absolute=<value>` (or Arducam's
  focuser utility with live preview) to dial in sharp focus at the real
  feeding-station distance, then set that value once at boot (systemd
  service / `rc.local`). No continuous AF hunting once set.
- Cable length: keep CSI runs to ~300–500mm and routed away from the
  stepper/servo/fan wiring (EMI risk). If the real enclosure layout needs
  more distance than that, use an **Arducam CSI-to-HDMI extension kit**
  (3–5m range, plug-and-play) rather than pushing a long bare FPC cable.

**Revised cost vs original submission BOM:**

| Item | Original | Revised | Note |
|---|---|---|---|
| AI accelerator | ~$115 (AI HAT+) | ~$135 (Mouser HM21LB1C2LAE) | different part, HAT+ doesn't work here |
| Cameras ×2 | ~$160 (Camera Module 3) | ~$71.10 (2× AC-B0393) | native cable, next-day ship |
| GPIO/actuation items | ~$98 | ~$98 | unchanged |
| **Total** | **~$373** | **~$304** | |

Still cheaper overall despite the Hailo line going up slightly, mostly from
the camera swap. Stepper+driver, servo, load cell, and audio amp+speaker are
still needed per the original BOM (§3.2) — not required until Week 3.

