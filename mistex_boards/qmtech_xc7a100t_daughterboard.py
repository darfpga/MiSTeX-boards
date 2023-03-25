#!/usr/bin/env python3
#
# This file is part of MiSTeX-Boards.
#
# Copyright (c) 2023 Hans Baier <hansfbaier@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause
#

from os.path import join
import sys
import yaml

from colorama import Fore, Style

from migen import *
from litex.build.generic_platform import *
from litex_boards.platforms import qmtech_artix7_fgg676

from litex.soc.cores.clock import S7PLL

from util import *

# Build --------------------------------------------------------------------------------------------

class Top(Module):
    def __init__(self, platform) -> None:
        #sdram       = platform.request("sdram")
        vga         = platform.request("vga")
        sdcard      = platform.request("sdcard")
        seven_seg   = platform.request("seven_seg")
        audio       = platform.request("audio")
        hps_spi     = platform.request("hps_spi")
        hps_control = platform.request("hps_control")
        debug       = platform.request("debug")

        sys_top = Instance("sys_top",
            i_CLK_50 = ClockSignal(),

            # TODO: HDMI
            #o_HDMI_I2C_SCL,
            #io_HDMI_I2C_SDA,
            #
            #o_HDMI_MCLK,
            #o_HDMI_SCLK,
            #o_HDMI_LRCLK,
            #o_HDMI_I2S,
            #
            #o_HDMI_TX_CLK,
            #o_HDMI_TX_DE,
            #o_HDMI_TX_D,
            #o_HDMI_TX_HS,
            #o_HDMI_TX_VS,
            #i_HDMI_TX_INT,

            #o_SDRAM_A = sdram.a,
            #io_SDRAM_DQ = sdram.dq,
            #o_SDRAM_DQML = sdram.dm[0],
            #o_SDRAM_DQMH = sdram.dm[1],
            #o_SDRAM_nWE = sdram.we_n,
            #o_SDRAM_nCAS = sdram.cas_n,
            #o_SDRAM_nRAS = sdram.ras_n,
            #o_SDRAM_nCS = sdram.cs_n,
            #o_SDRAM_BA = sdram.ba,
            #o_SDRAM_CLK = platform.request("sdram_clock"),
            #o_SDRAM_CKE = sdram.cke,

            o_VGA_R = Cat(False, [s for s in reversed(vga.r)]),
            o_VGA_G = Cat(       [s for s in reversed(vga.g)]),
            o_VGA_B = Cat(False, [s for s in reversed(vga.b)]),
            io_VGA_HS = vga.hsync_n,
            o_VGA_VS = vga.vsync_n,

            o_AUDIO_L = audio.l,
            o_AUDIO_R = audio.r,
            o_AUDIO_SPDIF = audio.spdif,

            o_LED_USER = platform.request("user_led", 0),
            o_LED_HDD = platform.request("user_led", 1),
            o_LED_POWER = platform.request("user_led", 2),
            i_BTN_USER = platform.request("user_btn", 0),
            i_BTN_OSD = platform.request("user_btn", 1),
            i_BTN_RESET = platform.request("user_btn", 2),

            o_SD_SPI_CS = sdcard.cd,
            i_SD_SPI_MISO = sdcard.data[0],
            o_SD_SPI_CLK = sdcard.clk,
            o_SD_SPI_MOSI = sdcard.cmd,

            io_SDCD_SPDIF = audio.sbcd_spdif,

            o_LED = seven_seg,

            i_HPS_SPI_MOSI = hps_spi.mosi,
            o_HPS_SPI_MISO = hps_spi.miso,
            i_HPS_SPI_CLK = hps_spi.clk,
            i_HPS_SPI_CS = hps_spi.cs_n,

            i_HPS_FPGA_ENABLE = hps_control.fpga_enable,
            i_HPS_OSD_ENABLE = hps_control.osd_enable,
            i_HPS_IO_ENABLE = hps_control.io_enable,
            i_HPS_CORE_RESET = hps_control.core_reset,
            o_DEBUG = debug
        )

        self.specials += sys_top

def main(core):
    coredir = join("cores", core)

    mistex_yaml = yaml.load(open(join(coredir, "MiSTeX.yaml"), 'r'), Loader=yaml.FullLoader)

    platform = qmtech_artix7_fgg676.Platform(with_daughterboard=True)

    add_designfiles(platform, coredir, mistex_yaml, 'vivado')

    defines = [
        ('XILINX', 1),
        # ('LARGE_FPGA', 1),

        # ('DEBUG_HPS_OP', 1),

        # do not enable DEBUG_NOHDMI in release!
        ('MISTER_DEBUG_NOHDMI', 1),

        # disable bilinear filtering when downscaling
        ('MISTER_DOWNSCALE_NN', 1),

        # disable adaptive scanline filtering
        #('MISTER_DISABLE_ADAPTIVE', 1),

        # use only 1MB per frame for scaler to free ~21MB DDR3 RAM
        #('MISTER_SMALL_VBUF', 1),

        # Disable YC / Composite output to save some resources
        ('MISTER_DISABLE_YC', 1),

        # Disable ALSA audio output to save some resources
        ('MISTER_DISABLE_ALSA', 1),
    ]

    for key, value in mistex_yaml.get('defines', {}).items():
        defines.append((key, value))

    build_id_path = generate_build_id(platform, coredir, defines)
    platform.toolchain.pre_synthesis_commands += [
        f'set_property is_global_include true [get_files "../../../{build_id_path}"]',
        'set_property default_lib work [current_project]'
    ]

    # TODO
    # platform.add_platform_command('set_false_path -from [get_clocks clk_sys] -to [get_clocks clk_audio]')

    add_mainfile(platform, coredir, mistex_yaml)

    platform.add_extension([
        ("audio", 0,
            Subsignal("l",          Pins("pmoda:0")),
            Subsignal("r",          Pins("pmoda:1")),
            Subsignal("spdif",      Pins("pmoda:2")),
            Subsignal("sbcd_spdif", Pins("pmoda:3")),
            IOStandard("LVCMOS33")
        ),
        ("hps_spi", 0,
            Subsignal("mosi", Pins("pmodb:0")),
            Subsignal("miso", Pins("pmodb:1")),
            Subsignal("clk",  Pins("pmodb:2")),
            Subsignal("cs_n", Pins("pmodb:3")),
            IOStandard("LVCMOS33"),
        ),
        ("hps_control", 0,
            Subsignal("fpga_enable", Pins("pmodb:4")),
            Subsignal("osd_enable",  Pins("pmodb:5")),
            Subsignal("io_enable",   Pins("pmodb:6")),
            Subsignal("core_reset",  Pins("pmodb:7")),
            IOStandard("LVCMOS33"),
        ),
        ("debug", 0, Pins("J1:18 J1:16 J1:14 J1:12"),
                     IOStandard("LVCMOS33")),
    ])

    platform.build(Top(platform),
        build_dir     = get_build_dir(core),
        build_name    = core.replace("-", "_"))

if __name__ == "__main__":
    handle_main(main)
