/*
 * Copyright (c) 2024 Jayden Cho
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none //error proof

module tt_um_uwasic_onboarding_jayden_cho ( //declaration or initialization

    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

  assign uio_oe = 8'hFF; //makes uio only outputs

  // ----------------------------------------------------------
  // Five 8-bit wires, one for each register in the register map.
  //   0x00 -> en_reg_out_7_0    (turn outputs 0-7 on/off)
  //   0x01 -> en_reg_out_15_8   (turn outputs 8-15 on/off)
  //   0x02 -> en_reg_pwm_7_0    (PWM on/off for outputs 0-7)
  //   0x03 -> en_reg_pwm_15_8   (PWM on/off for outputs 8-15)
  //   0x04 -> pwm_duty_cycle    (how "bright" PWM is, 0x00-0xFF)
  //
  // Right now nothing puts values on these wires yet.
  // In a later stage, YOUR SPI module will fill them in
  // based on the messages the controller sends.
  // ----------------------------------------------------------
  wire [7:0] en_reg_out_7_0;
  wire [7:0] en_reg_out_15_8;
  wire [7:0] en_reg_pwm_7_0;
  wire [7:0] en_reg_pwm_15_8;
  wire [7:0] pwm_duty_cycle;

  // ----------------------------------------------------------
  // Place the PWM module (already written for you, in
  // pwm_peripheral.v) inside your chip and plug wires into it.
  //
  // Format:  module_type  your_name_for_this_copy ( connections );
  //
  // Each connection looks like:  .its_pin_name(your_wire)
  // Read ".clk(clk)" as: "plug its clk pin into my clk wire."
  // ----------------------------------------------------------
  pwm_peripheral pwm_peripheral_inst (
    .clk(clk),                          // Give it the chip's clock.
    .rst_n(rst_n),                      // Give it the reset signal.
    .en_reg_out_7_0(en_reg_out_7_0),    // Give it the 5 register values...
    .en_reg_out_15_8(en_reg_out_15_8),
    .en_reg_pwm_7_0(en_reg_pwm_7_0),
    .en_reg_pwm_15_8(en_reg_pwm_15_8),
    .pwm_duty_cycle(pwm_duty_cycle),    // ...so it knows what each pin should do.

    // The module produces 16 output bits. The { } glue two
    // 8-bit groups into one 16-bit group:
    //   left side  (uio_out) gets the top 8    -> outputs 15 to 8
    //   right side (uo_out)  gets the bottom 8 -> outputs 7 to 0
    .out({uio_out, uo_out})
  );

  //declares what doesn't need to be used, they must be declared initially to avoid error messages
  wire _unused = &{ena, ui_in[7:3], uio_in, 1'b0};

endmodule
