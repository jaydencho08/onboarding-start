## How it works

This project uses SPI to control 16 outputs. Each output can be off, on, or PWM.
The system clock is 10 MHz. SPI uses mode 0 at about 100 kHz.

The inputs are SCLK on ui_in[0], COPI on ui_in[1], and nCS on ui_in[2].
The outputs are uo_out[7:0] and uio_out[7:0]. All uio pins are set to outputs.

Send 16 bits, most significant bit first: 1 write bit, 7 address bits, then 8
data bits. A write bit of 0 is ignored. The registers are:

- 0x00: enable outputs 0 to 7
- 0x01: enable outputs 8 to 15
- 0x02: enable PWM on outputs 0 to 7
- 0x03: enable PWM on outputs 8 to 15
- 0x04: duty cycle for all PWM outputs

The SPI inputs use two flip-flops each to sync with the system clock. Data is
sampled on rising SCLK edges. Registers change when nCS goes high after exactly
16 bits. Invalid addresses and messages with the wrong number of bits are ignored.
Keep nCS low during the message. Leave at least 1 us before the first clock,
after the last clock, and between messages. Use 5 us for each SCLK half-cycle.
Wait 1 us after nCS goes high before checking the updated output.

An output is low if its enable bit is 0. If enabled, it is high when PWM is off
and follows PWM when PWM is on. Frequency is 10 MHz / (13 * 256), about 3004.8 Hz.
Duty cycle is the register value divided by 256, except 255 gives 100%.
Zero gives 0%. Updates can change a pulse partway through a period, so wait for
the new setting to settle before measuring. Reset is active low and clears
all five registers, the SPI state, and the PWM counters and outputs.

## How to test

Install Python 3.11, make, and Icarus Verilog on Linux or WSL. From the repo:

```
python -m pip install -r test/requirements.txt
cd test
make
```

The tests check SPI writes, reads, invalid addresses, wrong message lengths,
and reset. PWM tests check all 256 duty values, frequency from 2970 to 3030 Hz,
and which outputs are enabled. Duty tolerance is one percentage point, with
0 and 255 checked for constant low and high. The tests run on RTL and the
gate-level netlist. Results are in results.xml and waveforms are in tb.vcd.

To try it on a board, send 0x80FF and 0x81FF to enable the outputs, then 0x82FF
and 0x83FF to enable PWM. Send 0x8480 for 50%, 0x8400 for 0%, or 0x84FF for 100%.
GitHub Actions runs the tests, builds the documentation and GDS, checks the
layout, and publishes the viewer.

## External hardware

Use a mode-0 SPI controller, a 10 MHz clock, and a logic analyzer or oscilloscope.
Use a common ground and the correct logic voltage for the Tiny Tapeout board.
LEDs need resistors. Power loads need external drivers.
