## How it works

This design controls 16 static or PWM outputs through a write-only SPI peripheral.
It uses a 10 MHz system clock and SPI mode 0 at approximately 100 kHz. Send each
16-bit packet most-significant bit first: one write bit (`1`), seven address bits,
then eight data bits. Read packets (`0`) and addresses outside `0x00`-`0x04` are ignored.

| Address | Register | Reset |
| --- | --- | --- |
| `0x00` | Output enables for `uo_out[7:0]` | `0x00` |
| `0x01` | Output enables for `uio_out[7:0]` | `0x00` |
| `0x02` | PWM enables for `uo_out[7:0]` | `0x00` |
| `0x03` | PWM enables for `uio_out[7:0]` | `0x00` |
| `0x04` | Shared PWM duty setting | `0x00` |

`ui_in[0]` is SCLK, `ui_in[1]` is COPI/MOSI, and `ui_in[2]` is active-low
chip select. All bidirectional pins are configured as outputs (`uio_oe = 0xFF`).
There is no CIPO/MISO output.

Two flip-flops synchronize each SPI input into the system-clock domain. The
receiver captures COPI on synchronized SCLK rising edges and commits the register
only on the synchronized rising edge of chip select. Frames shorter or longer
than 16 bits are rejected. Keep chip select low for the entire frame; provide at
least 1 us of setup before the first clock and hold after the final clock, and
at least 1 us high between frames. Nominal SCLK high/low times are each 5 us.
Allow 1 us after releasing chip select before inspecting updated outputs.

An output-enable bit of zero forces its output low. When enabled, a pin is
constant high if its PWM-enable bit is zero, or follows the shared PWM signal
otherwise. The divider advances an eight-bit PWM counter every 13 clock cycles:
`10,000,000 / (13 * 256) = 3004.807692 Hz`, within the 3 kHz +/-1% requirement.
Duty is `setting / 256`, except `0xFF` explicitly gives 100%. `0x00` gives 0%.
Duty and enable changes take effect immediately after the register update;
changing them in the middle of a PWM period can shorten or lengthen that pulse.
Measurements should use complete periods after the update has settled.

Active-low reset asynchronously clears the SPI state, all five registers, and
the PWM counters/output. The provided PWM behavior is retained; its divider
counter is sized to four bits, sufficient to count from 0 through 12.

## How to test

With Python 3.11, GNU Make, and Icarus Verilog installed:

```sh
python -m pip install -r test/requirements.txt
cd test
make
```

Use Linux or WSL for the Makefile. GitHub Actions runs the same tests on Ubuntu.
The original SPI test is retained. Added checks cover:

- Measured rising-edge PWM frequency at five duty settings, within 2970-3030 Hz.
- All 256 duty settings on all 16 pins, within one percentage point, with exact
  always-low and always-high checks at the endpoints.
- Static output, PWM output, disabled-output precedence, mixed masks, and each
  output individually.
- Atomic writes at chip-select release, read commands, every invalid address,
  varied data and SPI phase, inactive chip select, malformed frames, and reset
  during a transaction.

Tests use only top-level ports, so the same suite runs against the synthesized
gate-level netlist. `results.xml` contains the test results and `tb.vcd` contains
port-level waveforms. The GitHub workflows build documentation, run RTL tests,
generate GDS, run physical prechecks and gate-level tests, and deploy the layout
viewer through GitHub Pages.

For a bench check, send `0x80FF` and `0x81FF` to enable all outputs, `0x82FF` and
`0x83FF` to enable PWM, then `0x8480` for 50% duty. Observe approximately 3 kHz on
every output. Send `0x8400` for always low or `0x84FF` for always high.

## External hardware

A controller capable of SPI mode 0, a 10 MHz clock source, and a logic analyzer
or oscilloscope are sufficient. LEDs require suitable current-limiting resistors;
power loads require external drivers. Connect a common ground and use logic
levels compatible with the Tiny Tapeout board.
