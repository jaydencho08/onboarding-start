/*
 * Copyright (c) 2026 Jayden Cho
 * SPDX-License-Identifier: Apache-2.0
 */
`default_nettype none

module spi_peripheral (
    input wire clk,
    input wire rst_n,
    input wire sclk,
    input wire copi,
    input wire ncs,
    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);
    (* ASYNC_REG = "TRUE" *) reg [1:0] sclk_sync;
    (* ASYNC_REG = "TRUE" *) reg [1:0] copi_sync;
    (* ASYNC_REG = "TRUE" *) reg [1:0] ncs_sync;
    reg sclk_previous;
    reg ncs_previous;
    reg active;
    reg [15:0] packet;
    reg [4:0] bit_count;

    wire sclk_rising = sclk_sync[1] && !sclk_previous;
    wire ncs_falling = !ncs_sync[1] && ncs_previous;
    wire ncs_rising = ncs_sync[1] && !ncs_previous;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_sync <= 2'b00;
            copi_sync <= 2'b00;
            ncs_sync <= 2'b11;
            sclk_previous <= 1'b0;
            ncs_previous <= 1'b1;
        end else begin
            sclk_sync <= {sclk_sync[0], sclk};
            copi_sync <= {copi_sync[0], copi};
            ncs_sync <= {ncs_sync[0], ncs};
            sclk_previous <= sclk_sync[1];
            ncs_previous <= ncs_sync[1];
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            packet <= 16'b0;
            bit_count <= 5'd0;
            en_reg_out_7_0 <= 8'b0;
            en_reg_out_15_8 <= 8'b0;
            en_reg_pwm_7_0 <= 8'b0;
            en_reg_pwm_15_8 <= 8'b0;
            pwm_duty_cycle <= 8'b0;
        end else if (ncs_falling) begin
            active <= 1'b1;
            packet <= 16'b0;
            bit_count <= 5'd0;
        end else if (ncs_rising) begin
            active <= 1'b0;

            if (active && bit_count == 5'd16 && packet[15]) begin
                case (packet[14:8])
                    7'h00: en_reg_out_7_0 <= packet[7:0];
                    7'h01: en_reg_out_15_8 <= packet[7:0];
                    7'h02: en_reg_pwm_7_0 <= packet[7:0];
                    7'h03: en_reg_pwm_15_8 <= packet[7:0];
                    7'h04: pwm_duty_cycle <= packet[7:0];
                    default: begin end
                endcase
            end
        end else if (active && !ncs_sync[1] && sclk_rising) begin
            if (bit_count < 5'd16)
                packet <= {packet[14:0], copi_sync[1]};

            if (bit_count < 5'd17)
                bit_count <= bit_count + 5'd1;
        end
    end
endmodule
