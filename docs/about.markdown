---
layout: page
title: About
permalink: /about/
---

**PawsAndWait** is an element14 RoadTest of the [Raspberry Pi Compute Module 5 Development Kit][roadtest], built around an AI-powered smart pet feeder with animal recognition and pose detection.

Two real problems, one CM5:

- Feeding two dogs remotely — while still making them sit and wait before the food drops
- Keeping birds out of an outdoor cat bowl, using real-time species detection to hold the lid shut until the cat (and only the cat) is confirmed at the bowl

The build exercises the CM5's dual MIPI CSI camera inputs, the M.2 PCIe slot (a Hailo-8L AI accelerator), GPIO for motor and servo actuation, I2C sensors, and eMMC storage for a local database and web dashboard — benchmarking CPU-only inference against Hailo-accelerated inference along the way.

Source and full test plan:

- [RoadTest listing on element14 Community][roadtest]
- [Project repository on GitHub][repo]
- [Original submission idea][submission-idea]

[roadtest]: https://community.element14.com/products/roadtest/rt/roadtests/710/test-out-the-raspberry-pi-compute-module-5-development-kit
[repo]: https://github.com/saramic/paws-and-wait
[submission-idea]: https://github.com/saramic/learning/blob/master/ideation/2026_element14_road_test_PI_compute_5/SUBMISSION.md
