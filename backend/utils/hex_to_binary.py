HEX_TO_BINARY_CONVERSION_TABLE = {
    '0': '0000',
    '1': '0001',
    '2': '0010',
    '3': '0011',
    '4': '0100',
    '5': '0101',
    '6': '0110',
    '7': '0111',
    '8': '1000',
    '9': '1001',
    'a': '1010',
    'b': '1011',
    'c': '1100',
    'd': '1101',
    'e': '1110',
    'f': '1111'
}

def hex_to_binary(hex_str):
    binart_str = ''

    for char in hex_str:
        binart_str+=HEX_TO_BINARY_CONVERSION_TABLE[char]

    return binart_str

def main():
    n = 451
    h = hex(n)[2:]
    binary_number = hex_to_binary(h)

    print(binary_number)

    print(int(binary_number,2))


if __name__ == "__main__":
    main()