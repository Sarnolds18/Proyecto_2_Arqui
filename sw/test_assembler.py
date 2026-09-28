import os
import unittest

import assembler as asm


class TestEncodingFormats(unittest.TestCase):
    """Cross-check each instruction format against its bit layout, computed
    by hand from the RV32I encoding (funct7|rs2|rs1|funct3|rd|opcode, etc.)."""

    def test_r_type_add(self):
        # add a0, a1, a2 -> rd=10, rs1=11, rs2=12, funct3=0, funct7=0, opcode=0x33
        word = asm.encode_r(0x33, 10, 0b000, 11, 12, 0b0000000)
        expected = (0 << 25) | (12 << 20) | (11 << 15) | (0b000 << 12) | (10 << 7) | 0x33
        self.assertEqual(word, expected)
        self.assertEqual(word, 0x00C58533)

    def test_r_type_sub_sets_funct7_bit5(self):
        word = asm.encode_r(0x33, 5, 0b000, 5, 6, 0b0100000)
        self.assertEqual((word >> 25) & 0x7F, 0b0100000)

    def test_i_type_addi_positive(self):
        # addi t0, x0, 5 -> rd=5, rs1=0, imm=5, funct3=0, opcode=0x13
        word = asm.encode_i(0x13, 5, 0b000, 0, 5)
        self.assertEqual(word, (5 << 20) | (0 << 15) | (0 << 12) | (5 << 7) | 0x13)

    def test_i_type_addi_negative_two_complement(self):
        # addi t0, x0, -1 -> imm field must be 0xFFF (12-bit two's complement)
        word = asm.encode_i(0x13, 5, 0b000, 0, -1)
        imm_field = (word >> 20) & 0xFFF
        self.assertEqual(imm_field, 0xFFF)

    def test_s_type_sw_splits_immediate(self):
        # sw a4, 4(s0) -> rs2=14 (a4), rs1=8 (s0), imm=4, funct3=2, opcode=0x23
        word = asm.encode_s(0x23, 0b010, 8, 14, 4)
        imm_hi = (word >> 25) & 0x7F
        imm_lo = (word >> 7) & 0x1F
        self.assertEqual((imm_hi << 5) | imm_lo, 4)
        self.assertEqual((word >> 20) & 0x1F, 14)
        self.assertEqual((word >> 15) & 0x1F, 8)

    def test_b_type_offset_roundtrip(self):
        # A branch 12 bytes back (offset -12) must decode back to -12 when
        # the scattered bit_12/10:5/4:1/11 fields are reassembled.
        word = asm.encode_b(0x63, 0b001, 5, 6, -12)
        bit_12 = (word >> 31) & 0x1
        bits_10_5 = (word >> 25) & 0x3F
        bit_11 = (word >> 7) & 0x1
        bits_4_1 = (word >> 8) & 0xF
        imm = (bit_12 << 12) | (bit_11 << 11) | (bits_10_5 << 5) | (bits_4_1 << 1)
        if imm & (1 << 12):
            imm -= (1 << 13)
        self.assertEqual(imm, -12)

    def test_b_type_rejects_odd_offset(self):
        with self.assertRaises(ValueError):
            asm.encode_b(0x63, 0b000, 0, 0, 3)

    def test_u_type_lui(self):
        word = asm.encode_u(0x37, 8, 0x80000)  # lui s0, 0x80000
        self.assertEqual(word, (0x80000 << 12) | (8 << 7) | 0x37)

    def test_j_type_offset_roundtrip(self):
        word = asm.encode_j(0x6f, 0, -8)  # jal x0, <8 bytes back>
        bit_20 = (word >> 31) & 0x1
        bits_19_12 = (word >> 12) & 0xFF
        bit_11 = (word >> 20) & 0x1
        bits_10_1 = (word >> 21) & 0x3FF
        imm = (bit_20 << 20) | (bits_19_12 << 12) | (bit_11 << 11) | (bits_10_1 << 1)
        if imm & (1 << 20):
            imm -= (1 << 21)
        self.assertEqual(imm, -8)


class TestOperandParsing(unittest.TestCase):

    def test_register_by_abi_name(self):
        self.assertEqual(asm.parse_register("s0"), 8)
        self.assertEqual(asm.parse_register("a5"), 15)
        self.assertEqual(asm.parse_register("zero"), 0)

    def test_register_by_x_name(self):
        self.assertEqual(asm.parse_register("x15"), 15)

    def test_register_above_rv32e_range_rejected(self):
        with self.assertRaises(ValueError):
            asm.parse_register("x16")
        with self.assertRaises(ValueError):
            asm.parse_register("s2")  # s2 is x18, valid ABI name but not on RV32E...

    def test_immediate_hex_bin_dec(self):
        self.assertEqual(asm.parse_immediate("0x1F"), 31)
        self.assertEqual(asm.parse_immediate("0b101"), 5)
        self.assertEqual(asm.parse_immediate("-12"), -12)
        self.assertEqual(asm.parse_immediate("42"), 42)

    def test_mem_operand(self):
        self.assertEqual(asm.parse_mem_operand("4(s0)"), (4, 8))
        self.assertEqual(asm.parse_mem_operand("0(s0)"), (0, 8))
        self.assertEqual(asm.parse_mem_operand("-8(sp)"), (-8, 2))


class TestValidation(unittest.TestCase):
    """Errors the assembler must catch instead of silently miscompiling."""

    def _assemble(self, src):
        code = asm.drop_comments(asm.code_to_list(src))
        return asm.assemble(code)

    def test_unknown_instruction_rejected(self):
        with self.assertRaises(asm.AssemblerError):
            self._assemble("frobnicate x0, x0, x0\n")

    def test_out_of_range_immediate_rejected(self):
        with self.assertRaises(asm.AssemblerError):
            self._assemble("addi x1, x0, 5000\n")  # 12-bit signed max is 2047

    def test_duplicate_label_rejected(self):
        with self.assertRaises(asm.AssemblerError):
            self._assemble("foo: addi x0,x0,0\nfoo: addi x0,x0,0\n")

    def test_undefined_label_rejected(self):
        with self.assertRaises(asm.AssemblerError):
            self._assemble("beq x0, x0, nowhere\n")

    def test_rv32e_register_rejected(self):
        with self.assertRaises(asm.AssemblerError):
            self._assemble("add x16, x0, x0\n")

    def test_unsupported_directive_rejected(self):
        with self.assertRaises(asm.AssemblerError):
            self._assemble(".data\naddi x0,x0,0\n")

    def test_shift_emits_warning_not_error(self):
        code = asm.drop_comments(asm.code_to_list("slli x1, x1, 2\n"))
        warnings = []
        words = asm.assemble(code, warnings)
        self.assertEqual(len(words), 1)
        self.assertEqual(len(warnings), 1)
        self.assertIsInstance(warnings[0], asm.AssemblerWarning)


class TestLabelsAndBranches(unittest.TestCase):

    def test_forward_and_backward_label_offsets(self):
        src = (
            "start:\n"
            "    beq x0, x0, skip\n"   # addr 0, target addr 8 -> +8
            "    addi x0, x0, 0\n"     # addr 4 (skipped)
            "skip:\n"
            "    jal x0, start\n"      # addr 8, target addr 0 -> -8
        )
        code = asm.drop_comments(asm.code_to_list(src))
        words = asm.assemble(code)
        self.assertEqual(len(words), 3)

        # First word: beq x0,x0,skip, offset should be +8.
        imm = ((words[0] >> 31) & 1) << 12 | ((words[0] >> 7) & 1) << 11 \
            | ((words[0] >> 25) & 0x3F) << 5 | ((words[0] >> 8) & 0xF) << 1
        self.assertEqual(imm, 8)

        # Third word: jal x0,start, offset should be -8.
        w = words[2]
        bit_20 = (w >> 31) & 1
        imm_j = (bit_20 << 20) | (((w >> 12) & 0xFF) << 12) | (((w >> 20) & 1) << 11) \
            | (((w >> 21) & 0x3FF) << 1)
        if imm_j & (1 << 20):
            imm_j -= (1 << 21)
        self.assertEqual(imm_j, -8)


class TestGameRegression(unittest.TestCase):
    """Assembling the real game program must reproduce the committed hex
    exactly -- this is the check used before every FPGA demo/regen."""

    def test_game_s_matches_committed_game_hex(self):
        here = os.path.dirname(os.path.abspath(__file__))
        src_path = os.path.join(here, "game.s")
        hex_path = os.path.join(here, "game.hex")

        code = asm.drop_comments(asm.code_to_list(asm.read_file(src_path)))
        words = asm.assemble(code)
        produced = asm.to_hex(words)

        with open(hex_path) as f:
            committed = f.read()

        self.assertEqual(produced, committed)


if __name__ == "__main__":
    unittest.main()
