"""cocotb testbench for sync_fifo.sv.

Timing convention used in this file (learn it - you'll reuse it):
    * inputs are DRIVEN just after a FALLING clock edge
    * the DUT samples them at the next RISING edge
    * outputs are READ at the following FALLING edge, when everything has settled
This avoids races between your testbench and the DUT at the rising edge.
See docs/04-verification-basics.md.

Provided for you: FifoModel (the reference model), start(), cycle(), check(),
and two finished tests as worked examples. You write the rest.
"""

import random
from collections import deque

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge

DEPTH = 8
DWIDTH = 16
MASK = (1 << DWIDTH) - 1


class FifoModel:
    """Plain-Python model of what the FIFO SHOULD do. The DUT is compared against this.

    Rules (same as the spec in README.md):
      - a write is accepted only if wr_en and the FIFO is not full
      - a read is accepted only if rd_en and the FIFO is not empty
      - both flags are judged BEFORE the clock edge
      - dout changes only on an accepted read; otherwise it holds
    """

    def __init__(self):
        self.q = deque()
        self.dout = 0

    @property
    def empty(self):
        return len(self.q) == 0

    @property
    def full(self):
        return len(self.q) == DEPTH

    def step(self, wr_en, rd_en, din):
        do_w = wr_en and not self.full
        do_r = rd_en and not self.empty
        if do_r:
            self.dout = self.q.popleft()
        if do_w:
            self.q.append(din & MASK)


async def start(dut):
    """Start the clock, reset the DUT, return a fresh model. Ends on a falling edge."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    return FifoModel()


async def cycle(dut, model, wr_en=0, rd_en=0, din=0):
    """Run ONE clock cycle with the given inputs and compare ALL outputs to the model."""
    dut.wr_en.value = wr_en
    dut.rd_en.value = rd_en
    dut.din.value = din
    model.step(wr_en, rd_en, din)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    check(dut, model)


def check(dut, model):
    assert int(dut.empty.value) == int(model.empty), f"empty: got {dut.empty.value}, expected {int(model.empty)}"
    assert int(dut.full.value) == int(model.full), f"full: got {dut.full.value}, expected {int(model.full)}"
    assert int(dut.dout.value) == model.dout, f"dout: got {int(dut.dout.value):#x}, expected {model.dout:#x}"


# --------------------------------------------------------------------------- worked examples


@cocotb.test()
async def test_reset_state(dut):
    """After reset: empty, not full, dout is 0."""
    await start(dut)
    assert dut.empty.value == 1, "FIFO should be empty after reset"
    assert dut.full.value == 0, "FIFO should not be full after reset"
    assert dut.dout.value == 0, "dout should be 0 after reset"


@cocotb.test()
async def test_write_then_read_in_order(dut):
    """Write three words, read them back: same values, same order."""
    model = await start(dut)
    values = [0x1111, 0x2222, 0x3333]
    for v in values:
        await cycle(dut, model, wr_en=1, din=v)
    assert dut.empty.value == 0
    for v in values:
        await cycle(dut, model, rd_en=1)
        assert dut.dout.value == v, f"expected {v:#x} next"
    assert dut.empty.value == 1, "FIFO should be empty after reading everything"


# --------------------------------------------------------------------------- your tests


@cocotb.test()
async def test_fill_to_full(dut):
    """TODO: write DEPTH words. `full` must stay 0 until the last one, then be 1.
    Read them all back in order and check `empty` at the end."""
    model = await start(dut)
    words = [ 0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777, 0x8888]
    for i,w in enumerate(words):
        await cycle(dut, model, wr_en = 1, din = w)
        if i == DEPTH - 1:
            assert dut.full.value == 1
        else:
            assert dut.full.value == 0
    for w in words:
        await cycle(dut, model, rd_en = 1)
        assert dut.dout.value == w, f"expected {w:#x} next"
    assert dut.empty.value == 1




@cocotb.test()
async def test_write_when_full_is_ignored(dut):
    """TODO: fill the FIFO, attempt extra writes, then read everything back.
    The extra values must NOT appear and the original DEPTH words must be intact."""
    model = await start(dut)
    words = [ 0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777, 0x8888]
    for w in words:
        await cycle(dut, model, wr_en = 1, din = w)
    assert dut.full.value == 1
    words_extra = [0x9999, 0x1010]
    for w in words_extra:
        await cycle(dut, model, wr_en = 1, din = w)
    assert dut.full.value == 1
    for w in words:
        await cycle(dut, model, rd_en = 1)
        assert dut.dout.value == w, f"expected {w:#x} next"
    assert dut.empty.value == 1
    

@cocotb.test()
async def test_read_when_empty_is_ignored(dut):
    """TODO: read from an empty FIFO a couple of times (flags and dout must not change),
    then do a normal write+read and check it still works (pointers didn't get corrupted)."""
    model = await start(dut)
    assert dut.empty.value == 1
    for i in range(2):
        await cycle(dut, model, rd_en = 1)
        assert dut.dout.value == 0
        assert dut.empty.value == 1
        assert dut.full.value == 0
    await cycle(dut, model, wr_en = 1, din = 0x1111)
    await cycle(dut, model, rd_en = 1)
    assert dut.dout.value == 0x1111
    assert dut.empty.value == 1
    

@cocotb.test()
async def test_simultaneous_read_write(dut):
    """TODO: pre-load a few words, then assert wr_en and rd_en together for many cycles.
    The model already handles this case - just call cycle() and let check() compare."""
    model = await start(dut)
    words = [0x1111, 0x2222, 0x3333]
    for w in words:
        await cycle(dut, model, wr_en=1, din=w)
    for i in range(10):
        await cycle(dut, model, wr_en=1, rd_en = 1, din=i)
     

@cocotb.test()
async def test_pointer_wraparound(dut):
    """TODO: push/pop enough words (several times DEPTH) that the pointers wrap around
    past the end of memory repeatedly. Wrap bugs hide until then."""
    model = await start(dut)
    words = [ 0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777, 0x8888]
    for i in range(5):
        for w in words:
            await cycle(dut, model, wr_en = 1, din = w)
        assert dut.full.value == 1
        for w in words:
            await cycle(dut, model, rd_en = 1)
            assert dut.dout.value == w, f"expected {w:#x} next"
        assert dut.empty.value == 1

@cocotb.test()
async def test_random_traffic(dut):
    """TODO: 1000+ cycles of random wr_en / rd_en / din via cycle(). The model + check()
    do the verifying. Use random.Random(seed) with a fixed seed so a failure is reproducible,
    and print the seed in your assertion messages if you make it configurable."""
    model = await start(dut)
    r = random.Random(30)
    for i in range(1000):
        await cycle(dut, model, wr_en = r.randint(0,1), rd_en = r.randint(0,1), din=r.randint(0,MASK))