import os
from pathlib import Path
import pytest
import random
import cocotb
from cocotb.triggers import Timer
from cocotb.clock import Clock
from cocotb_bus.drivers.amba import AXI4LiteMaster
from cocotb.runner import get_runner
from system_version import *

debug_mode = int(os.getenv("PYCHARM_DEBUG", "0"))

if debug_mode:
    import pydevd_pycharm


CLK_PERIOD_NS = 10

testdata = [
    (
        random.randint(0, SYSTEM_VERSION_FPGA_VERSION_MAJ_MASK >> SYSTEM_VERSION_FPGA_VERSION_MAJ_OFFSET),
        random.randint(0, SYSTEM_VERSION_FPGA_VERSION_MIN_MASK >> SYSTEM_VERSION_FPGA_VERSION_MIN_OFFSET),
        random.randint(0, 2 ** 32 - 1)
    )
]

async def tb_setup(dut):
    dut.s_axi_aresetn.value = 0

    axim = AXI4LiteMaster(dut, "s_axi", dut.s_axi_aclk)
    cocotb.start_soon(Clock(dut.s_axi_aclk, CLK_PERIOD_NS, units="ns").start())

    await Timer(CLK_PERIOD_NS * 10, units='ns')

    dut.s_axi_aresetn.value = 1
    return axim


@cocotb.test()
async def reset_values_test(dut):
    if debug_mode:
        pydevd_pycharm.settrace('localhost', port=9090, stdoutToServer = True, stderrToServer = True)

    board_type = random.randint(0, 2**int(os.getenv("PARAM_C_BOARD_TYPE_WIDTH", "4")) - 1)
    board_rev = random.randint(0, 2 ** int(os.getenv("PARAM_C_BOARD_REV_WIDTH", "4")) - 1)

    dut.board_type.value = board_type
    dut.board_rev.value = board_rev

    axim = await tb_setup(dut)

    value = await system_version_read_board_type(axim)
    assert value == board_type, ("Board type should have been 0x%02X but was 0x%02X" % (board_type, int(value)))

    value = await system_version_read_board_rev(axim)
    assert value == board_rev, ("Board rev should have been 0x%02X but was 0x%02X" % (board_rev, int(value)))

    version_maj = int(os.getenv("PARAM_C_VER_MAJ", "0"))
    value = await system_version_fpga_version_maj(axim)
    assert value == version_maj, ("FPGA version major should have been 0x%02X but was 0x%02X" % (version_maj,
                                                                                                 int(value)))
    version_min = int(os.getenv("PARAM_C_VER_MIN", "0"))
    value = await system_version_fpga_version_min(axim)
    assert value == version_min, ("FPGA version minor should have been 0x%02X but was 0x%02X" % (version_min,
                                                                                                 int(value)))
    version_build = int(os.getenv("PARAM_C_VER_BUILD", "0"))
    value = await system_version_fpga_version_build(axim)
    assert value == version_build, ("FPGA version build should have been 0x%02X but was 0x%02X" % (version_build,
                                                                                                   int(value)))

@pytest.mark.parametrize("ver_maj,ver_min,ver_build", testdata)
def test_system_version_runner(ver_maj, ver_min, ver_build):
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent

    sources = [proj_path / ".." / "hdl" / "systemversion_v1_0.v"]

    parameters = {
        'C_VER_MAJ': ver_maj,
        'C_VER_MIN': ver_min,
        'C_VER_BUILD': ver_build,
        'C_BOARD_TYPE_WIDTH': 4,
        'C_BOARD_REV_WIDTH': 4
    }

    extra_env = {f'PARAM_{k}': str(v) for k, v in parameters.items()}

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="systemversion",
        defines={"SIM": 1, "NOTIMESCALE": 1},
        parameters=parameters,
        waves=True
    )

    runner.test(hdl_toplevel="systemversion",
                test_module="test_system_version,",
                waves=True,
                extra_env=extra_env,
                parameters=parameters,
                log_file="test_system_version.log")


if __name__ == "__main__":
    test_system_version_runner()
