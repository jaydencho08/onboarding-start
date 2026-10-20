# SPDX-FileCopyrightText: Copyright 2026 Jayden Cho
# SPDX-License-Identifier: Apache-2.0
"""Black-box SPI/PWM checks shared by RTL and gate-level simulations."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer
from cocotb.utils import get_sim_time

CLOCK_NS = 100
PERIOD_CYCLES = 13 * 256


def outputs(dut):
    return (int(dut.uio_out.value) << 8) | int(dut.uo_out.value)


async def setup(dut):
    dut.ena.value = 1
    dut.ui_in.value = 4
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    cocotb.start_soon(Clock(dut.clk, CLOCK_NS, units="ns").start())
    await ClockCycles(dut.clk, 10)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    await FallingEdge(dut.clk)
    assert outputs(dut) == 0, "Reset must disable every output"
    assert int(dut.uio_oe.value) == 0xFF


async def finish_frame(dut):
    dut.ui_in.value = 4
    await Timer(1000, units="ns")


async def frame(dut, bits, finish=True, half_ns=5000):
    # Deliberately offset SPI transitions from system-clock edges.
    await Timer(37, units="ns")
    dut.ui_in.value = 0
    await Timer(1000, units="ns")
    for bit in bits:
        dut.ui_in.value = bit << 1
        await Timer(half_ns, units="ns")
        dut.ui_in.value = (bit << 1) | 1
        await Timer(half_ns, units="ns")
    dut.ui_in.value = 0
    await Timer(1000, units="ns")
    if finish:
        await finish_frame(dut)


def packet_bits(address, data, write=True):
    word = (int(write) << 15) | (address << 8) | data
    return [(word >> bit) & 1 for bit in range(15, -1, -1)]


async def write_register(dut, address, value):
    await frame(dut, packet_bits(address, value))


async def configure(dut, enable=0xFFFF, pwm=0xFFFF, duty=128):
    for addr, value in enumerate((enable & 255, enable >> 8,
                                  pwm & 255, pwm >> 8, duty)):
        await write_register(dut, addr, value)


async def check_pwm_frequency(dut):
    await setup(dut)
    await configure(dut)
    for duty in (1, 64, 128, 192, 254):
        await write_register(dut, 4, duty)
        previous = outputs(dut)
        edges = []
        # Bounded sampling also turns a stuck output into a useful failure.
        for _ in range(3 * PERIOD_CYCLES):
            await FallingEdge(dut.clk)
            value = outputs(dut)
            assert value in (0, 0xFFFF), "All 16 PWM outputs must agree"
            if value == 0xFFFF and previous == 0:
                edges.append(get_sim_time(units="ns"))
                if len(edges) == 3:
                    break
            previous = value
        assert len(edges) >= 2, f"PWM stuck or too slow at duty {duty}"
        for start, end in zip(edges, edges[1:]):
            frequency = 1e9 / (end - start)
            assert 2970 <= frequency <= 3030, (duty, frequency)
        dut._log.info("Duty %d: measured PWM frequency %.6f Hz", duty, frequency)


async def check_pwm_duty(dut):
    await setup(dut)
    await configure(dut)
    # Two whole nominal periods remove phase dependence. Frequency is checked
    # independently above, so an incorrect divider cannot hide in this average.
    samples = 2 * PERIOD_CYCLES
    for duty in range(256):
        await write_register(dut, 4, duty)
        high = 0
        for _ in range(samples):
            await FallingEdge(dut.clk)
            value = outputs(dut)
            assert value in (0, 0xFFFF), f"Channel mismatch at duty {duty}"
            high += value == 0xFFFF
        expected = 1.0 if duty == 255 else duty / 256.0
        measured = high / samples
        assert abs(measured - expected) <= 0.01, (duty, measured, expected)
        if duty in (0, 255):
            assert high == (samples if duty == 255 else 0), "Endpoint glitch"
    dut._log.info("All 256 duty settings passed on all 16 output pins")


async def check_output_modes(dut, enable, pwm, duty):
    static = enable & ~pwm & 0xFFFF
    modulated = enable & pwm
    high = 0
    samples = 2 * PERIOD_CYCLES
    for _ in range(samples):
        await FallingEdge(dut.clk)
        value = outputs(dut)
        assert value & (~enable & 0xFFFF) == 0, "Disabled output went high"
        assert value & static == static, "Static output went low"
        assert value in (static, static | modulated), "PWM channels disagree"
        if modulated:
            high += (value & modulated) == modulated
    if modulated:
        expected = 1.0 if duty == 255 else duty / 256.0
        assert abs(high / samples - expected) <= 0.01
        if duty in (0, 255):
            assert high == (samples if duty == 255 else 0)
