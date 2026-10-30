// game_rom: imagen del programa como ROM combinacional.
// ARCHIVO GENERADO, no editar a mano.
// PROVISORIA: generada desde sw/game.hex por scripts/rom_provisoria.py.
// Se reemplaza por la salida de sw/assembler.py (debe dar el mismo contenido).

module game_rom (
  input  wire [7:0]  addr_i,  // direccion de palabra
  output reg  [31:0] data_o
);

  always @* begin
    case (addr_i)
      8'd0: data_o = 32'h80000437;
      8'd1: data_o = 32'h00c42483;
      8'd2: data_o = 32'h00000513;
      8'd3: data_o = 32'h00000593;
      8'd4: data_o = 32'h00042023;
      8'd5: data_o = 32'h00c42603;
      8'd6: data_o = 32'h00f00293;
      8'd7: data_o = 32'h00542223;
      8'd8: data_o = 32'h04787337;
      8'd9: data_o = 32'h8c030313;
      8'd10: data_o = 32'h00c42383;
      8'd11: data_o = 32'h40c383b3;
      8'd12: data_o = 32'hfe63cce3;
      8'd13: data_o = 32'h007484b3;
      8'd14: data_o = 32'h6f74c493;
      8'd15: data_o = 32'h00c484b3;
      8'd16: data_o = 32'h0034f693;
      8'd17: data_o = 32'h00100713;
      8'd18: data_o = 32'h02068063;
      8'd19: data_o = 32'h00200713;
      8'd20: data_o = 32'h00100293;
      8'd21: data_o = 32'h00568a63;
      8'd22: data_o = 32'h00400713;
      8'd23: data_o = 32'h00200293;
      8'd24: data_o = 32'h00568463;
      8'd25: data_o = 32'h00800713;
      8'd26: data_o = 32'h00e42223;
      8'd27: data_o = 32'h00c42603;
      8'd28: data_o = 32'h00842283;
      8'd29: data_o = 32'hfe029ee3;
      8'd30: data_o = 32'h00842283;
      8'd31: data_o = 32'hfe028ee3;
      8'd32: data_o = 32'h00c42303;
      8'd33: data_o = 32'h40c30333;
      8'd34: data_o = 32'h04e29863;
      8'd35: data_o = 32'h002623b7;
      8'd36: data_o = 32'h5a038393;
      8'd37: data_o = 32'h00000793;
      8'd38: data_o = 32'h00734863;
      8'd39: data_o = 32'h40730333;
      8'd40: data_o = 32'h00178793;
      8'd41: data_o = 32'hff5ff06f;
      8'd42: data_o = 32'h00f585b3;
      8'd43: data_o = 32'h00150513;
      8'd44: data_o = 32'h090000ef;
      8'd45: data_o = 32'h00c42603;
      8'd46: data_o = 32'h02faf337;
      8'd47: data_o = 32'h08030313;
      8'd48: data_o = 32'h00c42383;
      8'd49: data_o = 32'h40c383b3;
      8'd50: data_o = 32'hfe63cce3;
      8'd51: data_o = 32'h00a00293;
      8'd52: data_o = 32'h04550063;
      8'd53: data_o = 32'hf3dff06f;
      8'd54: data_o = 32'h00042223;
      8'd55: data_o = 32'h0ee00293;
      8'd56: data_o = 32'h00542023;
      8'd57: data_o = 32'h00262337;
      8'd58: data_o = 32'h5a030313;
      8'd59: data_o = 32'h00500293;
      8'd60: data_o = 32'h00028e63;
      8'd61: data_o = 32'h00c42603;
      8'd62: data_o = 32'h00c42383;
      8'd63: data_o = 32'h40c383b3;
      8'd64: data_o = 32'hfe63cce3;
      8'd65: data_o = 32'hfff28293;
      8'd66: data_o = 32'hfe9ff06f;
      8'd67: data_o = 32'hf05ff06f;
      8'd68: data_o = 32'h00a00393;
      8'd69: data_o = 32'h00000793;
      8'd70: data_o = 32'h0075c863;
      8'd71: data_o = 32'h407585b3;
      8'd72: data_o = 32'h00178793;
      8'd73: data_o = 32'hff5ff06f;
      8'd74: data_o = 32'h018000ef;
      8'd75: data_o = 32'h00842283;
      8'd76: data_o = 32'hfe029ee3;
      8'd77: data_o = 32'h00842283;
      8'd78: data_o = 32'hfe028ee3;
      8'd79: data_o = 32'hec5ff06f;
      8'd80: data_o = 32'h00a00293;
      8'd81: data_o = 32'h00000313;
      8'd82: data_o = 32'h0057c863;
      8'd83: data_o = 32'h405787b3;
      8'd84: data_o = 32'h00130313;
      8'd85: data_o = 32'hff5ff06f;
      8'd86: data_o = 32'h00900393;
      8'd87: data_o = 32'h00734663;
      8'd88: data_o = 32'h00900313;
      8'd89: data_o = 32'h00900793;
      8'd90: data_o = 32'h00000293;
      8'd91: data_o = 32'h00000393;
      8'd92: data_o = 32'h00638863;
      8'd93: data_o = 32'h01028293;
      8'd94: data_o = 32'h00138393;
      8'd95: data_o = 32'hff5ff06f;
      8'd96: data_o = 32'h00f282b3;
      8'd97: data_o = 32'h00542023;
      8'd98: data_o = 32'h00008067;
      default: data_o = 32'h00000000;
    endcase
  end

endmodule
