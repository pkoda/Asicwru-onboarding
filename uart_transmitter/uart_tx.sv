// UART transmitter -- 8-N-1 (8 data bits, no parity, 1 stop bit)
// See uart_transmitter/README.md for the full spec and timing diagram.
//
// CLK_FREQ_HZ / BAUD_RATE sets how many clk cycles make up one bit period.
// For simulation the Makefile overrides these to small values so tests finish quickly
// (CLK_FREQ_HZ=1000, BAUD_RATE=100 -> 10 clks/bit). Don't hardcode CLKS_PER_BIT yourself:
// compute it from the parameters.
//
// What to do:
//   IDLE is done for you as a worked example. Follow the same pattern to fill in START,
//   DATA, and STOP.
//
// Done when: see README.md.

module uart_tx #(
    parameter int CLK_FREQ_HZ = 50_000_000,
    parameter int BAUD_RATE   = 115_200
) (
    input  logic       clk,
    input  logic       rst_n,      // asynchronous, active-low reset

    input  logic       tx_start,   // pulse high for 1 cycle to begin sending tx_data
    input  logic [7:0] tx_data,

    output logic       tx,         // serial line; idles high
    output logic       tx_busy     // high while a frame is in flight
);

    localparam int CLKS_PER_BIT = CLK_FREQ_HZ / BAUD_RATE;   // assumes >= 2

    // Counter width, and the value at which one bit period is over. Comparing against a
    // constant of the SAME WIDTH as clk_count keeps the simulator's width checks quiet:
    // comparing a 4-bit counter with a 32-bit integer is flagged as a WIDTHEXPAND warning,
    // and the cocotb build treats warnings as errors.
    localparam int CW = $clog2(CLKS_PER_BIT);
    localparam logic [CW-1:0] LAST_COUNT = CW'(CLKS_PER_BIT - 1);

    typedef enum logic [1:0] {
        IDLE,
        START,
        DATA,
        STOP
    } state_t;

    state_t state;
    logic [CW-1:0] clk_count;    // counts clock cycles within the current bit
    logic [2:0]    bit_index;    // which data bit we're sending (0 = LSB)
    logic [7:0]    data_reg;     // latched copy of tx_data
    logic          tx_reg;

    assign tx      = tx_reg;
    assign tx_busy = (state != IDLE);

    // IMPORTANT - keep `tx` lined up with `state`.
    // tx_reg is a flip-flop, so what you assign to it now shows up on `tx` NEXT cycle, the
    // same moment `state` changes. That means tx_reg must be given the value of the bit you
    // are ABOUT TO send at the moment you change state, i.e. on the transition:
    //     entering START  -> tx_reg <= 0            (done for you in IDLE below)
    //     entering DATA   -> tx_reg <= data_reg[0]
    //     next data bit   -> tx_reg <= data_reg[bit_index + 1]
    //     entering STOP   -> tx_reg <= 1
    // If you instead set tx_reg <= data_reg[bit_index] at the top of DATA, tx lags `state`
    // by one cycle and tx_busy will fall a cycle before the last stop-bit cycle ends.

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= IDLE;
            clk_count <= '0;
            bit_index <= '0;
            data_reg  <= '0;
            tx_reg    <= 1'b1;   // idle high
        end else begin
            case (state)

                // --- worked example -------------------------------------
                // Sits at logic 1 until tx_start pulses. Then latches the byte, drives the
                // start bit (0), and moves on to START. tx_start is ignored in every other
                // state.
                IDLE: begin
                    tx_reg    <= 1'b1;
                    clk_count <= '0;
                    bit_index <= '0;
                    if (tx_start) begin
                        data_reg <= tx_data;
                        tx_reg   <= 1'b0;
                        state    <= START;
                    end
                end

                // --- TODO: START -----------------------------------------
                // Stay here for CLKS_PER_BIT cycles (count clk_count up to LAST_COUNT, then
                // reset it to 0). On the last cycle: tx_reg <= data_reg[0]; state <= DATA.
                START: begin
                    if (clk_count != LAST_COUNT) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 1'b0;
                        tx_reg   <= data_reg[0];
                        state <= DATA;
                    end
                end

                // --- TODO: DATA ------------------------------------------
                // Hold each data bit for CLKS_PER_BIT cycles. At the end of a bit period:
                //   - if bit_index is 7: bit_index <= 0; tx_reg <= 1; state <= STOP
                //   - otherwise:         bit_index++; tx_reg <= data_reg[bit_index + 1]
                DATA: begin
                    if (clk_count != LAST_COUNT) begin
                        clk_count <= clk_count + 1'b1;
                    end else begin
                        clk_count <= 1'b0;
                        if (bit_index == 7) begin
                            bit_index <= 3'd0;
                            tx_reg <= 1'b1;
                            state <= STOP;
                        end else begin
                            bit_index <= bit_index + 1'b1; 
                            tx_reg <= data_reg[bit_index + 1];
                        end
                    end

                end

                // --- TODO: STOP ------------------------------------------
                // Hold the line high for CLKS_PER_BIT cycles, then return to IDLE.
                STOP: begin
                    if (clk_count != LAST_COUNT) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 1'b0;
                        tx_reg   <= 1'b1;
                        state <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
