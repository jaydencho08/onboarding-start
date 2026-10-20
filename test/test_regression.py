# SPDX-FileCopyrightText: Copyright 2026 Jayden Cho
# SPDX-License-Identifier: Apache-2.0
import random
import cocotb
from cocotb.triggers import FallingEdge, Timer
from pwm_checks import (setup, outputs, frame, finish_frame, packet_bits,
                        write_register, configure, check_output_modes)


@cocotb.test()
async def test_spi_commit_and_frame_validation(dut):
    await setup(dut)
    await write_register(dut, 0, 0x5A)
    bits = packet_bits(0, 0xA5)
    await frame(dut, bits, finish=False)
    assert outputs(dut) == 0x5A, "Register changed before nCS rose"
    await finish_frame(dut)
    assert outputs(dut) == 0xA5

    for length in (0, 1, 7, 8, 15, 17, 31, 32, 48, 80):
        malformed = (packet_bits(0, 0xFF) * 5)[:length]
        await frame(dut, malformed)
        assert outputs(dut) == 0xA5, f"Accepted {length}-bit frame"
    # Clocks with CS inactive must not alter state.
    for _ in range(20):
        dut.ui_in.value = 7
        await Timer(5000, units="ns")
        dut.ui_in.value = 4
        await Timer(5000, units="ns")
    assert outputs(dut) == 0xA5
    await write_register(dut, 0, 0x3C)
    assert outputs(dut) == 0x3C, "Receiver did not recover after invalid frames"


@cocotb.test()
async def test_spi_addresses_reads_and_data(dut):
    await setup(dut)
    await configure(dut, enable=0xA55A, pwm=0x0FF0, duty=128)
    for address in range(5, 128):
        await write_register(dut, address, 0)
    for address in range(5):
        await frame(dut, packet_bits(address, 0, write=False))
    await check_output_modes(dut, 0xA55A, 0x0FF0, 128)

    # Verify both output banks, including every bit and different SPI phases.
    await configure(dut, enable=0, pwm=0, duty=0)
    rng = random.Random(2026)
    patterns = [0, 255, 0xAA, 0x55] + [1 << bit for bit in range(8)]
    patterns += [rng.randrange(256) for _ in range(20)]
    expected = [0, 0]
    for value in patterns:
        for address in (0, 1):
            await frame(dut, packet_bits(address, value),
                        half_ns=rng.choice((4901, 5000, 5107)))
            expected[address] = value
            assert outputs(dut) == (expected[1] << 8) | expected[0]


@cocotb.test()
async def test_pwm_output_enable_precedence(dut):
    await setup(dut)
    for enable, pwm in ((0, 0xFFFF), (0xFFFF, 0), (0xA55A, 0x0FF0),
                        (0x5AA5, 0xF00F), (0xFFFF, 0xFFFF)):
        for duty in (0, 128, 255):
            await configure(dut, enable, pwm, duty)
            await check_output_modes(dut, enable, pwm, duty)
    # Each pin independently switches from static to PWM to disabled.
    for bit in range(16):
        mask = 1 << bit
        await configure(dut, mask, mask, 128)
        await check_output_modes(dut, mask, mask, 128)


@cocotb.test()
async def test_reset_during_transaction(dut):
    await setup(dut)
    await configure(dut, duty=255)
    assert outputs(dut) == 0xFFFF
    await frame(dut, packet_bits(0, 0xFF)[:8], finish=False)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    await Timer(1000, units="ns")
    assert outputs(dut) == 0
    dut.ui_in.value = 4
    await Timer(1000, units="ns")
    dut.rst_n.value = 1
    await Timer(1000, units="ns")
    assert outputs(dut) == 0
    # Output mode registers reset to static; duty resets to zero.
    await write_register(dut, 0, 0xFF)
    await write_register(dut, 1, 0xFF)
    assert outputs(dut) == 0xFFFF
    await write_register(dut, 2, 0xFF)
    await write_register(dut, 3, 0xFF)
    assert outputs(dut) == 0
    await write_register(dut, 4, 255)
    assert outputs(dut) == 0xFFFF
