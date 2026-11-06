"""cocotb testbench for uart_tx.sv

CLKS_PER_BIT here MUST match CLK_FREQ_HZ / BAUD_RATE that the Makefile builds the DUT with
(1000 / 100 = 10). If you change one, change the other.

Timing convention (see docs/04-verification-basics.md):
    drive inputs just after a FALLING clock edge, read outputs at a FALLING clock edge.

What to do:
    reset_dut() is done for you as a worked example. Implement send_and_check_byte() below -
    every test calls it. Then add the extra tests listed at the bottom.

Done when: see uart_transmitter/README.md.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

CLKS_PER_BIT = 10


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.tx_start.value = 0
    dut.tx_data.value = 0
    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def send_and_check_byte(dut, byte_val, extra_start_at = None):
    """TODO: implement this.

    1. Set tx_data = byte_val and pulse tx_start high for exactly ONE cycle
       (set it, `await FallingEdge(dut.clk)`, clear it).
    2. Wait (a few cycles at most - use a bounded loop, never loop forever) for tx to go low,
       and assert that it did. That is the start of the start bit.
    3. Build the expected frame as a list of 10 bit values:
           [0] + [(byte_val >> i) & 1 for i in range(8)] + [1]
       Then for each bit, for each of its CLKS_PER_BIT cycles, assert that:
           - dut.tx equals the expected bit  (checks value AND exact duration)
           - dut.tx_busy is 1
       and `await FallingEdge(dut.clk)` to move to the next cycle.
    4. After the frame, allow at most 2 cycles for tx_busy to drop to 0, then assert it
       is 0 and that tx is back at 1.

    Write assertion messages that say WHICH bit and WHICH cycle failed.
    """
    dut.tx_data.value = byte_val
    dut.tx_start.value = 1
    await FallingEdge(dut.clk)
    dut.tx_start.value = 0
    start = False
    for i in range(3):
        await FallingEdge(dut.clk)
        if dut.tx.value == 0:
            start = True
            break
    assert start, "tx did not go low"
    expected = [0] + [(byte_val >> i) & 1 for i in range(8)] + [1]
    for bit_index, bit_value in enumerate(expected):
        for cycle in range(CLKS_PER_BIT):
            assert dut.tx.value == bit_value, f"Wrong value at bit {bit_index}, cycle{cycle}"
            assert dut.tx_busy.value == 1, f"tx_busy went low at bit {bit_index}, cycle {cycle}"
            total_cycle = bit_index * CLKS_PER_BIT + cycle
            if total_cycle == extra_start_at:
                dut.tx_data.value = byte_val ^ 0xFF
                dut.tx_start.value = 1
                await FallingEdge(dut.clk)
                dut.tx_start.value = 0
            else:
                await FallingEdge(dut.clk)
    for i in range(2):
        if dut.tx_busy.value == 0:
            break
        await FallingEdge(dut.clk)
    assert dut.tx_busy.value == 0, "tx_busy did not return to 0"
    assert dut.tx.value == 1, "tx did not return to high"




@cocotb.test()
async def test_idles_high(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    for _ in range(3 * CLKS_PER_BIT):
        assert dut.tx.value == 1, "tx should idle high"
        assert dut.tx_busy.value == 0, "tx_busy should be low when idle"
        await FallingEdge(dut.clk)


@cocotb.test()
async def test_single_byte(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    await send_and_check_byte(dut, 0xA5)


@cocotb.test()
async def test_edge_case_bytes(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    for val in [0x00, 0xFF, 0x01, 0x80]:
        await send_and_check_byte(dut, val)


@cocotb.test()
async def test_random_bytes(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    rng = random.Random(42)   # fixed seed: failures are reproducible
    for _ in range(20):
        await send_and_check_byte(dut, rng.randint(0, 255))


# ---------------------------------------------------------------------------- YOUR TESTS
# TODO: add these (each is a normal @cocotb.test() like the ones above):
#
#   test_back_to_back        - send several bytes in a row with no idle gap between calls
#
#   test_start_ignored_while_busy
#                            - while a frame is in flight, pulse tx_start again with DIFFERENT
#                              data. The in-flight frame must finish unchanged, and the extra
#                              request must not start a second frame. (Hint: add an optional
#                              argument to send_and_check_byte that fires the extra pulse at a
#                              chosen cycle inside its loop.)
#
#   test_reset_mid_frame     - reset the DUT halfway through a frame; tx must return to 1 and
#                              tx_busy to 0, and a fresh frame afterwards must still be correct.

@cocotb.test()
async def test_back_to_back(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    for val in [0xA1, 0xA2, 0xA3, 0x3C, 0xF0]:
        await send_and_check_byte(dut, val)

@cocotb.test()
async def test_start_ignored_while_busy(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    await send_and_check_byte(dut, 0xA5, extra_start_at=20)
    for i in range(CLKS_PER_BIT * 2):
        assert dut.tx.value == 1, "unexpected second frame"
        assert dut.tx_busy.value == 0, "unexpected second frame"
        await FallingEdge(dut.clk)

        
@cocotb.test()
async def test_reset_mid_frame(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    dut.tx_data.value = 0xA5
    dut.tx_start.value = 1
    await FallingEdge(dut.clk)
    dut.tx_start.value = 0
    await FallingEdge(dut.clk)
    assert dut.tx.value == 0
    assert dut.tx_busy.value == 1
    for i in range(CLKS_PER_BIT * 3):
        await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    await FallingEdge(dut.clk)
    assert dut.tx.value == 1, "tx did not go to 1 after reset"
    assert dut.tx_busy.value == 0, "tx_busy did not clear after reset"

    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    await send_and_check_byte(dut, 0xA4)


