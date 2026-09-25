def parse_register(tok: str) -> int:
    try:
        if tok[0]!="x":
            raise ValueError
        reg = int(tok.strip("x"))
        if not 0<=reg<=15:
            raise ValueError
        return reg
    except ValueError:
        print(f"direction: '{tok}' doesn't exist on RV32E")

def parse_immediate(tok:str) -> int:
    try: 
        number = int(tok, 0)
        return number
    except ValueError:
        print(f"value: '{tok}' is not decimal, hex or binary")

def parse_mem_operand(tok: str) -> tuple:
    try:
        offset, registerNumber = tok.split("(")
        offset = parse_immediate(offset)
        registerNumber = parse_register(registerNumber.strip(")"))
        if offset == None or registerNumber == None:
            raise ValueError
        return (offset, registerNumber)
    except ValueError:
        print(f"mem operand: {tok} does not exist in RV32E")


tok = "5(x16)"
reg = parse_mem_operand(tok)
if reg:
    print(reg)