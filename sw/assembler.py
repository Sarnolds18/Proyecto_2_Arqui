import sys


class AssemblerError(ValueError):
    """An error in the assembly source, printed like a compiler diagnostic."""

    def __init__(self, message: str, line_no: int, source: str, filename: str = "<input>"):
        super().__init__(message)
        self.message = message
        self.line_no = line_no
        self.source = source
        self.filename = filename

    def __str__(self) -> str:
        code = self.source.rstrip().expandtabs(4)
        column = len(code) - len(code.lstrip()) + 1
        underline = "^" + "~" * (len(code.strip()) - 1)
        gutter = " " * len(str(self.line_no))
        return (f"{self.filename}:{self.line_no}:{column}: error: {self.message}\n"
                f" {self.line_no} | {code}\n"
                f" {gutter} | {' ' * (column - 1)}{underline}")


# Every supported instruction: mnemonic -> (format, opcode, funct3, funct7).
# Fields a format doesn't use are None. funct3 values match the comments in
# rtl/espino_core/espino_decoder.v; funct7 0b0100000 is what the decoder
# reads as funct7[5] to tell sub/sra/srai apart from add/srl/srli.
INSTRUCTIONS = {
    # R-type: rd, rs1, rs2
    "add":   ("R", 0x33, 0b000, 0b0000000),
    "sub":   ("R", 0x33, 0b000, 0b0100000),
    "sll":   ("R", 0x33, 0b001, 0b0000000),
    "slt":   ("R", 0x33, 0b010, 0b0000000),
    "sltu":  ("R", 0x33, 0b011, 0b0000000),
    "xor":   ("R", 0x33, 0b100, 0b0000000),
    "srl":   ("R", 0x33, 0b101, 0b0000000),
    "sra":   ("R", 0x33, 0b101, 0b0100000),
    "or":    ("R", 0x33, 0b110, 0b0000000),
    "and":   ("R", 0x33, 0b111, 0b0000000),

    # I-type arithmetic: rd, rs1, imm
    "addi":  ("I", 0x13, 0b000, None),
    "slti":  ("I", 0x13, 0b010, None),
    "sltiu": ("I", 0x13, 0b011, None),
    "xori":  ("I", 0x13, 0b100, None),
    "ori":   ("I", 0x13, 0b110, None),
    "andi":  ("I", 0x13, 0b111, None),

    # Shifts by immediate: rd, rs1, shamt (execute as ADD on this core!)
    "slli":  ("SHIFT", 0x13, 0b001, 0b0000000),
    "srli":  ("SHIFT", 0x13, 0b101, 0b0000000),
    "srai":  ("SHIFT", 0x13, 0b101, 0b0100000),

    # Loads: rd, imm(rs1)
    "lb":    ("LOAD", 0x03, 0b000, None),
    "lh":    ("LOAD", 0x03, 0b001, None),
    "lw":    ("LOAD", 0x03, 0b010, None),
    "lbu":   ("LOAD", 0x03, 0b100, None),
    "lhu":   ("LOAD", 0x03, 0b101, None),

    # Stores: rs2, imm(rs1)
    "sb":    ("S", 0x23, 0b000, None),
    "sh":    ("S", 0x23, 0b001, None),
    "sw":    ("S", 0x23, 0b010, None),

    # Branches: rs1, rs2, label
    "beq":   ("B", 0x63, 0b000, None),
    "bne":   ("B", 0x63, 0b001, None),
    "blt":   ("B", 0x63, 0b100, None),
    "bge":   ("B", 0x63, 0b101, None),
    "bltu":  ("B", 0x63, 0b110, None),
    "bgeu":  ("B", 0x63, 0b111, None),

    # Upper immediate: rd, imm20
    "lui":   ("U", 0x37, None, None),
    "auipc": ("U", 0x17, None, None),

    # Jumps
    "jal":   ("J", 0x6f, None, None),       # rd, label
    "jalr":  ("JALR", 0x67, 0b000, None),   # rd, imm(rs1)
}

# How many operands each format takes in the source.
OPERAND_COUNT = {"R": 3, "I": 3, "SHIFT": 3, "LOAD": 2, "S": 2,
                 "B": 3, "U": 2, "J": 2, "JALR": 2}

def read_file(file_path: str) -> str:
    """Return the contents of a text file, or "" if it can't be read."""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return ""
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""

def code_to_list(code: str) -> list:
    """Split source text into a list of lines."""
    return code.split("\n")

def drop_comments(code: list) -> list:
    """
    Strip '#' comments and trailing whitespace from every line.

    Lines are kept even when left empty, so code[i] is still source line
    i + 1 and errors can point at the right line.
    """
    lines = []
    for line in code:
        if "#" in line:
            line = line.split("#")[0]
        lines.append(line.rstrip())
    return lines

def find_labels(code: list) -> dict:
    """
    Map each label to the address of the instruction that follows it.

    Addresses start at 0 and advance 4 per instruction; labels and
    directives take no space. Raises AssemblerError on a duplicate label.
    """
    labels = {}
    label_lines = {}
    address = 0
    for line_no, source in enumerate(code, start=1):
        line = source.strip()
        if not line:
            continue
        if line[0] == ".":
            continue
        if ":" in line:
            label, line = line.split(":", 1)
            label = label.strip()
            if label in labels:
                raise AssemblerError(
                    f"label '{label}' is already defined on line {label_lines[label]}",
                    line_no, source)
            labels[label] = address
            label_lines[label] = line_no
            line = line.strip()
            if not line:
                continue
        address += 4
    return labels

def print_code(code: list) -> None:
    """Print the non-empty lines with their source line numbers, for debugging."""
    width = len(str(len(code)))
    for line_no, line in enumerate(code, start=1):
        if not is_empty(line):
            print(f"{line_no:>{width}} | {line}")

def get_instructions(code: list) -> list:
    """
    Return (address, instruction, line_no) for every instruction line.

    Skips directives and empty lines, removes labels (keeping an
    instruction on the same line), and counts addresses like find_labels.
    line_no is the source line number, for error messages.
    """
    instructions = []
    address = 0
    for line_no, source in enumerate(code, start=1):
        line = source.strip()
        if is_empty(line) or line.startswith("."):
            continue
        if ":" in line:
            line = line.split(":", 1)[1].strip()
            if is_empty(line):
                continue
        instructions.append((address, line, line_no))
        address += 4
    return instructions

def tokenize(line: str) -> tuple:
    """
    Split an instruction into (mnemonic, operands).

    "SW x1, 0(x2)" -> ("sw", ["x1", "0(x2)"])
    """
    parts = line.strip().split(maxsplit=1)

    if not parts:
        return ("", [])
        
    op = parts[0].lower()

    if len(parts) < 2:
        return (op, [])
        
    directions = [arg.strip() for arg in parts[1].split(",") if arg.strip()]
    
    return (op, directions)

def parse_register(tok: str) -> int:
    """Return the number of register "x0".."x15". Raises ValueError otherwise."""
    name = tok.strip()
    if len(name) < 2 or name[0] != "x" or not name[1:].isdigit():
        raise ValueError(f"'{name}' is not a register (expected x0 to x15)")
    reg = int(name[1:])
    if not 0 <= reg <= 15:
        raise ValueError(f"register '{name}' doesn't exist on RV32E, which only has x0 to x15")
    return reg

def parse_immediate(tok: str) -> int:
    """
    Parse a decimal, 0x hex or 0b binary number (may be negative).

    Raises ValueError if tok isn't a number.
    """
    try:
        return int(tok.strip(), 0)
    except ValueError:
        raise ValueError(f"'{tok.strip()}' is not a valid number "
                         f"(expected decimal like 12, hex like 0x1F or binary like 0b101)") from None

def parse_mem_operand(tok: str) -> tuple:
    """
    Parse "offset(reg)" into (offset, reg_number); a missing offset is 0.

    Raises ValueError if the operand is malformed.
    """
    text = tok.strip()
    if "(" not in text or not text.endswith(")"):
        raise ValueError(f"'{text}' is not a valid memory operand "
                         f"(expected offset(register), e.g. 0(x2) or -8(x3))")
    offset, registerNumber = text[:-1].split("(", 1)
    offset = parse_immediate(offset) if not is_empty(offset.strip()) else 0
    registerNumber = parse_register(registerNumber)
    return (offset, registerNumber)

def to_bits(value: int, bits: int, signed: bool = True) -> int:
    """
    Return value as a bits-wide field, in two's complement if negative.

    Signed fields hold -2^(bits-1)..2^(bits-1)-1, unsigned ones 0..2^bits-1.
    Raises ValueError if value doesn't fit, instead of silently truncating.
    """
    if signed:
        low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    else:
        low, high = 0, (1 << bits) - 1
    if not low <= value <= high:
        kind = "signed" if signed else "unsigned"
        raise ValueError(f"value {value} is out of range for a {bits}-bit {kind} field "
                         f"(must be between {low} and {high})")
    mask = (1 << bits) - 1
    return value & mask

def encode_r(opcode: int, rd: int, funct3: int, rs1: int, rs2: int, funct7: int) -> int:
    """Pack an R-type instruction: funct7 | rs2 | rs1 | funct3 | rd | opcode."""
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

def encode_i(opcode: int, rd: int, funct3: int, rs1: int, imm: int) -> int:
    """Pack an I-type instruction: imm[11:0] | rs1 | funct3 | rd | opcode."""
    imm = to_bits(imm, 12)
    return (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

def encode_s(opcode: int, funct3: int, rs1: int, rs2: int, imm: int) -> int:
    """Pack an S-type instruction: imm[11:5] | rs2 | rs1 | funct3 | imm[4:0] | opcode."""
    imm = to_bits(imm, 12)
    imm_hi = imm >> 5          # imm[11:5]
    imm_lo = imm & 0x1F        # imm[4:0]
    return (imm_hi << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_lo << 7) | opcode

def encode_b(opcode: int, funct3: int, rs1: int, rs2: int, offset: int) -> int:
    """
    Pack a B-type instruction; offset is target - this address, in bytes.

    Offset must be even and fit in 13 signed bits (±4 KiB). Raises ValueError otherwise.
    """
    if offset % 2 != 0:
        raise ValueError(f"branch offset {offset} is odd, but branch targets must be at even addresses")
    try:
        imm = to_bits(offset, 13)
    except ValueError:
        raise ValueError(f"branch target is {offset} bytes away, but branches can only reach "
                         f"-4096 to +4094 bytes (use jal for longer jumps)") from None
    bit_12    = (imm >> 12) & 0x1
    bits_10_5 = (imm >> 5) & 0x3F
    bits_4_1  = (imm >> 1) & 0xF
    bit_11    = (imm >> 11) & 0x1
    return ((bit_12 << 31) | (bits_10_5 << 25) | (rs2 << 20) | (rs1 << 15)
            | (funct3 << 12) | (bits_4_1 << 8) | (bit_11 << 7) | opcode)

def encode_u(opcode: int, rd: int, imm20: int) -> int:
    """Pack a U-type instruction: imm20 goes straight into bits [31:12]."""
    imm20 = to_bits(imm20, 20, signed=False)
    return (imm20 << 12) | (rd << 7) | opcode

def encode_j(opcode: int, rd: int, offset: int) -> int:
    """
    Pack a J-type instruction; offset is target - this address, in bytes.

    Offset must be even and fit in 21 signed bits (±1 MiB). Raises ValueError otherwise.
    """
    if offset % 2 != 0:
        raise ValueError(f"jump offset {offset} is odd, but jump targets must be at even addresses")
    try:
        imm = to_bits(offset, 21)
    except ValueError:
        raise ValueError(f"jump target is {offset} bytes away, but jal can only reach "
                         f"-1048576 to +1048574 bytes (±1 MiB)") from None
    bit_20     = (imm >> 20) & 0x1
    bits_10_1  = (imm >> 1) & 0x3FF
    bit_11     = (imm >> 11) & 0x1
    bits_19_12 = (imm >> 12) & 0xFF
    return ((bit_20 << 31) | (bits_10_1 << 21) | (bit_11 << 20)
            | (bits_19_12 << 12) | (rd << 7) | opcode)

def label_offset(label: str, address: int, labels: dict) -> int:
    """Return the distance in bytes from address to label. Raises ValueError if it's undefined."""
    if label not in labels:
        raise ValueError(f"undefined label '{label}'")
    return labels[label] - address

def assemble_instruction(line: str, address: int, labels: dict) -> int:
    """
    Encode one instruction line into its 32-bit word.

    address is where the instruction lives (for branch/jump offsets).
    Raises ValueError on an unknown instruction, a wrong number of
    operands, or any invalid operand.
    """
    mnemonic, operands = tokenize(line)
    if mnemonic not in INSTRUCTIONS:
        raise ValueError(f"unknown instruction '{mnemonic}'")
    fmt, opcode, funct3, funct7 = INSTRUCTIONS[mnemonic]

    expected = OPERAND_COUNT[fmt]
    if len(operands) != expected:
        raise ValueError(f"'{mnemonic}' expects {expected} operands, got {len(operands)}")

    if fmt == "R":                                   # add rd, rs1, rs2
        rd, rs1, rs2 = (parse_register(op) for op in operands)
        return encode_r(opcode, rd, funct3, rs1, rs2, funct7)

    if fmt == "I":                                   # addi rd, rs1, imm
        rd, rs1 = parse_register(operands[0]), parse_register(operands[1])
        imm = parse_immediate(operands[2])
        return encode_i(opcode, rd, funct3, rs1, imm)

    if fmt == "SHIFT":                               # slli rd, rs1, shamt
        rd, rs1 = parse_register(operands[0]), parse_register(operands[1])
        shamt = parse_immediate(operands[2])
        if not 0 <= shamt <= 31:
            raise ValueError(f"shift amount {shamt} is out of range (must be between 0 and 31)")
        return encode_i(opcode, rd, funct3, rs1, (funct7 << 5) | shamt)

    if fmt in ("LOAD", "JALR"):                      # lw rd, imm(rs1)
        rd = parse_register(operands[0])
        imm, rs1 = parse_mem_operand(operands[1])
        return encode_i(opcode, rd, funct3, rs1, imm)

    if fmt == "S":                                   # sw rs2, imm(rs1)
        rs2 = parse_register(operands[0])
        imm, rs1 = parse_mem_operand(operands[1])
        return encode_s(opcode, funct3, rs1, rs2, imm)

    if fmt == "B":                                   # bne rs1, rs2, label
        rs1, rs2 = parse_register(operands[0]), parse_register(operands[1])
        offset = label_offset(operands[2], address, labels)
        return encode_b(opcode, funct3, rs1, rs2, offset)

    if fmt == "U":                                   # lui rd, imm20
        rd = parse_register(operands[0])
        imm20 = parse_immediate(operands[1])
        return encode_u(opcode, rd, imm20)

    if fmt == "J":                                   # jal rd, label
        rd = parse_register(operands[0])
        offset = label_offset(operands[1], address, labels)
        return encode_j(opcode, rd, offset)

    raise ValueError(f"format '{fmt}' of '{mnemonic}' is not supported")

def is_empty(string: str) -> bool:
    """Return True if string is empty or only whitespace."""
    return not string.strip()

if __name__ == "__main__":
    path = "sw/blink.s"
    try:
        code = code_to_list(read_file(path))
        codeNoComments = drop_comments(code)
        print_code(codeNoComments)
        codeLabels = find_labels(codeNoComments)
        print(codeLabels)
        instructions = get_instructions(codeNoComments)
        print(instructions)
        for i in instructions:
            print(tokenize(i[1]))
        print(instructions)
    except AssemblerError as e:
        e.filename = path
        print(e, file=sys.stderr)
        sys.exit(1)