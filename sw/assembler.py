def read_file(file_path: str) -> str:
    """
    Reads the content of a file and returns it as a string.

    Parameters:
    file_path (str): The path to the file.

    Returns:
    str: The content of the file.
    """
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
    """
    Converts the given code string into a list of lines.

    Parameters:
    code (str): The code string to convert.

    Returns:
    list: A list of lines from the code string.
    """
    return code.split("\n")

def drop_comments(code: list) -> list:
    """
    Removes '#' comments from the given list of lines.

    Everything from a '#' to the end of its line is dropped, along with
    trailing whitespace. Lines left empty are removed.

    Parameters:
    code (list): A list of lines from which to remove comments.

    Returns:
    list: A list of lines from the code string without comments.
    """
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
    Finds all labels in the given code and the address each one points to.

    Every instruction takes 4 bytes, starting at address 0. Directives
    (lines starting with '.') and labels do not take up space.

    Parameters:
    code (list): A list of lines from the code string in which to find labels.

    Returns:
    dict: A dictionary mapping each label to its address.
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
    """
    Prints the given code one line per row, numbered.

    Parameters:
    code (list): A list of lines to print.
    """
    width = len(str(len(code)))
    for i, line in enumerate(code, start=1):
        print(f"{i:>{width}} | {line}")

def get_instructions(code: list) -> list:
    """
    Returns a list of all instructions in the given code.

    Parameters:
    code (list): A list of lines from the code string.

    Returns:
    list: A list of instructions from the code string.
    """
    instructions = []
    adress = 0
    for line in code:
        lineInstructions = []
        if line.startswith("."):
            continue
        if ":" in line:
            line = line.split(":", 1)[1]
            if line=="" or line.isspace():
                continue
            lineInstructions.append(line)
        else:
            count = 0
            for char in line:
                if char!=" ":
                    break
                count+=1
            lineInstructions.append(line[count:])
        for inst in lineInstructions:
            instructions.append((adress, inst))
            adress += 4

    return instructions

def tokenize(line: str) -> tuple:
    parts = line.strip().split(maxsplit=1)

    if not parts:
        return ("", [])
        
    op = parts[0].lower()

    if len(parts) < 2:
        return (op, [])
        
    directions = [arg.strip() for arg in parts[1].split(",") if arg.strip()]
    
    return (op, directions)

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


def is_empty(string: str) -> bool:
    return string in ("", " ")

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