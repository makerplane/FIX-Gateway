
import struct

def build_crc_table():
    crc16table = []
    for i in range(256):
        crc = i << 8
        for bitctr in range(8):
            crc = (crc << 1) ^ (0x1021 if (crc & 0x8000) else 0)
        crc16table.append(crc)
    return crc16table


def calc_crc(msg: bytes):
    crc = 0
    for i in range(len(msg)):
        crc = CRC16TABLE[crc >> 8] ^ (crc << 8) ^ msg[i]
        crc = crc & 0xffff
    return crc


def decodeGDL90(msg: bytes):
    msg_cleaned = bytearray()
    ctr = 0
    n = 1
    while n < len(msg)-3:
        if (msg[n] == 0x7d) or (msg[n] == 0x7e):
            n += 1
            msg_cleaned.append(msg[n] ^ 0x20)
        else:
            msg_cleaned.append(msg[n])
        n += 1

    # Last byte should be 0x7E
    if msg[-1] != 0x7e:
        print("packet format error")

    msg_cleaned = bytes(msg_cleaned)  # struct.pack('B'*len(msg_cleaned), *msg_cleaned)
    msg_crc = struct.unpack('H', msg[-3:-1])[0]
    msg_calc_crc = calc_crc(msg_cleaned)
    # print(msg_cleaned)
    # print(msg_crc, msg_calc_crc)
    if msg_crc != msg_calc_crc:
        return b''

    return msg_cleaned


CRC16TABLE = build_crc_table()

# tstmsg = [0x7e, 0x0, 0x81, 0x41, 0xdb, 0xd0, 0x08, 0x02, 0xb3, 0x8b, 0x7e]
# tstmsg = struct.pack('B'*len(tstmsg), *tstmsg)
# print(hex(calc_crc(tstmsg[1:-3])))
# print(decodeGLD90(tstmsg))
