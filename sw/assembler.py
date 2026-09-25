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
    """Strip '#' comments and trailing whitespace; drop lines left empty."""
    lines = []
    for line in code:
        if "#" in line:
            line = line.split("#")[0].rstrip()
        if line=="" or line.isspace():
            continue
        lines.append(line)
    return lines

def find_labels(code: list) -> dict:
    """
    Map each label to the address of the instruction that follows it.

    Addresses start at 0 and advance 4 per instruction; labels and
    directives take no space. Raises ValueError on a duplicate label.
    """
    labels = {}
    address = 0
    for line in code:
        line = line.strip()
        if not line:
            continue
        if line[0] == ".":
            continue
        if ":" in line:
            label, line = line.split(":", 1)
            label = label.strip()
            if label in labels:
                raise ValueError(f"Duplicate label: {label}")
            labels[label] = address
            line = line.strip()
            if not line:
                continue
        address += 4
    return labels

def print_code(code: list) -> None:
    """Print lines with line numbers, for debugging."""
    width = len(str(len(code)))
    for i, line in enumerate(code, start=1):
        print(f"{i:>{width}} | {line}")

def get_instructions(code: list) -> list:
    """
    Return (address, instruction) for every instruction line.

    Skips directives and empty lines, removes labels (keeping an
    instruction on the same line), and counts addresses like find_labels.
    """
    instructions = []
    address = 0
    for line in code:
        line = line.strip()
        if is_empty(line) or line.startswith("."):
            continue
        if ":" in line:
            line = line.split(":", 1)[1].strip()
            if is_empty(line):
                continue
        instructions.append((address, line))
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
        raise ValueError(f"direction: '{tok}' doesn't exist on RV32E")
    reg = int(name[1:])
    if not 0 <= reg <= 15:
        raise ValueError(f"direction: '{tok}' doesn't exist on RV32E")
    return reg

def parse_immediate(tok: str) -> int:
    """
    Parse a decimal, 0x hex or 0b binary number (may be negative).

    Raises ValueError if tok isn't a number.
    """
    try:
        return int(tok.strip(), 0)
    except ValueError:
        raise ValueError(f"value: '{tok}' is not decimal, hex or binary") from None

def parse_mem_operand(tok: str) -> tuple:
    """
    Parse "offset(reg)" into (offset, reg_number); a missing offset is 0.

    Raises ValueError if the operand is malformed.
    """
    text = tok.strip()
    if "(" not in text or not text.endswith(")"):
        raise ValueError(f"mem operand: '{tok}' is not of the form offset(register)")
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
        raise ValueError(f"value {value} doesn't fit in {bits} {kind} bits ({low} to {high})")
    mask = (1 << bits) - 1
    return value & mask

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

def is_empty(string: str) -> bool:
    """Return True if string is empty or only whitespace."""
    return not string.strip()

if __name__ == "__main__":
    code = code_to_list(read_file("sw/blink.s"))
    codeNoComments = drop_comments(code)
    print_code(codeNoComments)
    codeLabels = find_labels(codeNoComments)
    print(codeLabels)
    instructions = get_instructions(codeNoComments)
    print(instructions)
    for i in instructions:
        print(tokenize(i[1]))
    print(instructions)