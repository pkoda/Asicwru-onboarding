/*
This is the testbench for the ALU you just built in alu.sv. A testbench is simulation-only code --
it will never be synthesized into real hardware, unlike alu.sv. Its job is to drive values onto the
ALU's input ports, give the combinational logic time to settle, and check that the result port holds
the value we expect. Because the ALU is purely combinational (no clk), there's no clock generation
to write here just stimulus and checking.
*/
 
`timescale 1ns / 1ps
 
module alu_tb;
 
/*
These are the testbench's own signals, not the ALU's ports and they're what the testbench uses to
drive and observe the DUT below. Anything the testbench needs to assign (the ALU's inputs) is
declared as "logic" so it can be driven from an initial block; the same is true of what the ALU
drives back to the testbench (the result), since we only ever read it here.
 
The widths below assume the port widths described in alu.sv (two 32-bit operands, a 4-bit opcode,
a 32-bit result). If you changed any of those widths, update these to match.
*/
 
logic [31:0] tb_input1;
logic [31:0] tb_input2;
logic [3:0]  tb_opcode;
logic [31:0] tb_result;
 
/*
DUT stands for "Design Under Test", the module actually being tested, as opposed to the testbench
wrapped around it. Instantiate your alu module here and connect each of its ports, by name, to the
testbench signals above: ".port_name(tb_signal_name)" for each port.

Hint:

Named connection means the order you declared ports in alu.sv doesn't matter here, and a typo in a
port name will be caught by the compiler instead of silently wiring the wrong signal together 
positional connection (just listing signals in order, with no port names) gives up both of those
safety nets, so don't use it here.
*/
 
alu DUT (
    .a(tb_input1),
    .b(tb_input2),
    .op(tb_opcode),
    .result(tb_result)
);
 
/*
Copy the localparams from alu.sv here so the stimulus below can refer to operations by name (ADD,
SUB, ...) instead of by raw 4-bit values. This list should be identical to the one in your alu.sv --
if it drifts out of sync, the testbench will be checking the wrong opcode against the wrong result.
*/
 
localparam ADD = 4'h0;
localparam SUB = 4'h1;
localparam AND = 4'h2;
localparam OR =  4'h3;
localparam XOR = 4'h4;
localparam SLL = 4'h5;
localparam SRL = 4'h6;
localparam SRA = 4'h7;
localparam SLT = 4'h8;
localparam SLTU = 4'h9;
/*
This task applies one test case: it drives both operands and the opcode onto the DUT, waits for the
combinational logic to settle, works out what the result *should* be for that opcode, and reports a
pass or fail. It's fully worked out for ADD so you can see the pattern -- fill in the rest of the
case branches to match every operation you implemented in alu.sv's always_comb block. Each branch
should compute "expected" the same way you'd expect the hardware to, using ordinary SystemVerilog
operators (+, -, &, |, ^, ~, <<, >>, <, ==) on a and b.
 
The "#1" is a delay of one simulation time unit. always_comb has no clock to trigger it, so the
simulator needs to be told to let time pass after the inputs change and before tb_result is read --
reading tb_result in the same instant the inputs change would still show the *previous* result.
 
Lastly, fill in a default branch for "expected", for the same reason alu.sv needed a default case:
so the check always has a defined value to compare against, even for an opcode you haven't handled.
*/
 
task automatic check_op(input logic [31:0] a, input logic [31:0] b, input logic [3:0] op,
                         input string op_name);
    logic [31:0] expected;
 
    tb_input1 = a;
    tb_input2 = b;
    tb_opcode = op;
    #1;
 
    case (op)
        ADD: expected = a + b;
        SUB: expected = a - b;
        AND: expected = a & b;
        OR:  expected = a | b;
        XOR: expected = a ^ b;
        SLL: expected = a << b[4:0];
        SRL: expected = a >> b[4:0];
        SRA: expected = $signed(a) >>> b[4:0];
        SLT: expected = {31'b0, $signed(a) < $signed(b)};   // result should read back as 1 or 0
        SLTU: expected = {31'b0, a < b };      // result should read back as 1 or 0
        default: expected = 0;
    endcase
 
    if (tb_result === expected) 
        $display("PASS: %-4s  a=%0d b=%0d  result=%0d", op_name, a, b, tb_result);
    else
        $display("FAIL: %-4s  a=%0d b=%0d  expected=%0d got=%0d", op_name, a, b, expected, tb_result);
    
endtask
 
/*
Call check_op once per operation, with input values chosen to actually exercise that operation and
not just any pair of numbers. ADD is given as an example. Add a call for every other opcode, and
think about what could go wrong for each one: SLT and EQ should each be tried once where the
comparison is true and once where it's false, SLL/SRL should use a shift amount that isn't zero, and
SUB should include a case where the result would go negative if your ALU treats it as signed.
*/

logic [31:0] random_a;
logic [31:0] random_b;
logic [3:0] random_op;
 
initial begin
    check_op(32'd10, 32'd20, ADD, "ADD");
    check_op(32'd10, 32'd20, SUB, "SUB");
    check_op(32'd10, 32'd20, AND, "AND");
    check_op(32'd10, 32'd20, OR, "OR");
    check_op(32'd10, 32'd20, XOR, "XOR");

    check_op(32'd8, 32'd2, SLL, "SLL");
    check_op(32'd1, 32'd32, SLL, "SLL");

    check_op(32'h80000000, 32'd1, SRL, "SRL");
    check_op(32'h80000000, 32'd1, SRA, "SRA");

    check_op(-32'sd2, 32'd5, SLT, "SLT");
    check_op(32'd10, 32'd5, SLT, "SLT");
    check_op(-32'sd2, 32'd5, SLTU, "SLTU");


    check_op(32'd10, 32'd20, 4'hA, "INVALID A");
    check_op(32'd10, 32'd20, 4'hB, "INVALID B");
    check_op(32'd10, 32'd20, 4'hC, "INVALID C");
    check_op(32'd10, 32'd20, 4'hD, "INVALID D");
    check_op(32'd10, 32'd20, 4'hE, "INVALID E");
    check_op(32'd10, 32'd20, 4'hF, "INVALID F");

    for (int i = 0; i < 1000; i++) begin
        random_a = $urandom;
        random_b = $urandom;
        random_op = $urandom_range(0, 15);

        check_op(random_a, random_b, random_op, "RANDOM");
end

    $finish;
end
 
endmodule
 