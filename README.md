[![CI](https://github.com/armin306/fastcs-carbide/actions/workflows/ci.yml/badge.svg)](https://github.com/armin306/fastcs-carbide/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/armin306/fastcs-carbide/branch/main/graph/badge.svg)](https://codecov.io/gh/armin306/fastcs-carbide)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# fastcs_carbide

FastCS IOC for the Light Conversion CARBIDE laser controller, part of the
Aithre (Diamond Light Source I23 laser-shaping lab) control software.
Mirrors [fastcs-rtc6](https://github.com/armin306/fastcs-rtc6)'s
shape and conventions - see that repo for the equivalent RTC6 scan-head IOC.

What            | Where
:---:           | :---:
Source          | <https://github.com/armin306/fastcs-carbide>
Docker          | `docker run ghcr.io/armin306/fastcs-carbide:latest`
Releases        | <https://github.com/armin306/fastcs-carbide/releases>
PVs             | [`docs/PV_LIST.md`](docs/PV_LIST.md)

Talks to the CARBIDE Supervisor REST API over HTTP and exposes it as an
EPICS IOC (via [FastCS](https://diamondlightsource.github.io/fastcs/main/index.html),
see also its [GitHub repo](https://github.com/DiamondLightSource/FastCS)),
with an [ophyd-async](https://github.com/bluesky/ophyd-async) device and
Bluesky plan stubs on top for eventual use from `dodal`/`mx-bluesky` - not
yet wired into either; see
[armin306/aithre](https://github.com/armin306/aithre/blob/docs/functional-spec/docs/FUNCTIONAL_SPEC.md)'s
`docs/FUNCTIONAL_SPEC.md` (`docs/functional-spec` branch) for the plan this
was built from, and `bin/laserControl.py` in
[DiamondLightSource/aithre](https://github.com/DiamondLightSource/aithre) for
the original (pre-FastCS) prototype this ports.

Start the IOC from a `fastcs.yaml` config file (see `fastcs.yaml` in this
repo for a working example):

```yaml
controllers:
  - id: LA18L-EA-CARB-01
    type: fastcs_carbide.CarbideController
    base_url: http://172.23.171.207:20010
transport:
  - epicsca: {}
```

```
fastcs-carbide run fastcs.yaml
```

Or as a library:

```python
from fastcs_carbide import __version__

print(f"Hello fastcs_carbide {__version__}")
```
