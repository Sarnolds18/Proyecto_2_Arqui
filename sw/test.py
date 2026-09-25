tok = "x1234"
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
    

reg = parse_register(tok)
if reg:
    print(reg)