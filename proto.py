from encrypt import enc_packet, dec_packet


def enc_varint(n):
    if n < 0: return b''
    h = []
    while True:
        b = n & 0x7F
        n >>= 7
        if n: b |= 0x80
        h.append(b)
        if not n: break
    return bytes(h)


def dec_varint(data, pos):
    res, shift = 0, 0
    while pos < len(data):
        b = data[pos]
        res |= (b & 0x7f) << shift
        pos += 1
        if not (b & 0x80): return res, pos
        shift += 7
    return 0, pos


def enc_uid(uid):
    uid_int = int(uid)
    e = []
    while uid_int:
        e.append((uid_int & 0x7F) | (0x80 if uid_int > 0x7F else 0))
        uid_int >>= 7
    return bytes(e).hex()


def create_variant(field_number, value):
    return enc_varint((field_number << 3) | 0) + enc_varint(value)


def create_length(field_number, value):
    encoded_value = value.encode('utf-8') if isinstance(value, str) else value
    return enc_varint((field_number << 3) | 2) + enc_varint(len(encoded_value)) + encoded_value


def create_proto(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    packet.extend(create_length(field, create_proto(item)))
                elif isinstance(item, int):
                    packet.extend(create_variant(field, item))
                elif isinstance(item, (str, bytes)):
                    packet.extend(create_length(field, item))
        elif isinstance(value, dict):
            packet.extend(create_length(field, create_proto(value)))
        elif isinstance(value, int):
            packet.extend(create_variant(field, value))
        elif isinstance(value, (str, bytes)):
            packet.extend(create_length(field, value))
    return bytes(packet)


def decode_proto(data):
    res_d = {}
    pos = 0
    while pos < len(data):
        try:
            tag, pos = dec_varint(data, pos)
            if tag == 0: break
            field_num = tag >> 3
            wire_type = tag & 0x07
            key = str(field_num)
            val = None
            if wire_type == 0:
                val, pos = dec_varint(data, pos)
            elif wire_type == 1:
                val = data[pos:pos+8].hex(); pos += 8
            elif wire_type == 2:
                length, pos = dec_varint(data, pos)
                chunk = data[pos:pos+length]; pos += length
                try:
                    s = chunk.decode('utf-8')
                    if all(32 <= ord(c) <= 126 or ord(c) > 160 for c in s):
                        val = s.strip()
                    else:
                        raise Exception
                except:
                    inner = decode_proto(chunk)
                    val = inner if inner else chunk.hex()
            elif wire_type == 5:
                val = data[pos:pos+4].hex(); pos += 4
            else:
                pos += 1; continue
            if val is not None:
                if key in res_d:
                    if not isinstance(res_d[key], list):
                        res_d[key] = [res_d[key]]
                    res_d[key].append(val)
                else:
                    res_d[key] = val
        except Exception:
            break
    return res_d


def generate_packet_plain(proto_hex, opcode):
    payload = bytes.fromhex(proto_hex)
    length_hex = hex(len(payload))[2:].zfill(2)
    if len(length_hex) == 2: header = opcode + "000000" + length_hex
    elif len(length_hex) == 3: header = opcode + "00000" + length_hex
    elif len(length_hex) == 4: header = opcode + "0000" + length_hex
    elif len(length_hex) == 5: header = opcode + "000" + length_hex
    else: header = opcode + length_hex
    return bytes.fromhex(header) + payload


def generate_packet(proto_hex, opcode, key, iv):
    encrypted_payload = enc_packet(proto_hex, key, iv)
    length_hex = hex(len(encrypted_payload) // 2)[2:].zfill(2)
    if len(length_hex) == 2: header = opcode + "000000" + length_hex
    elif len(length_hex) == 3: header = opcode + "00000" + length_hex
    elif len(length_hex) == 4: header = opcode + "0000" + length_hex
    elif len(length_hex) == 5: header = opcode + "000" + length_hex
    else: header = opcode + length_hex
    return bytes.fromhex(header + encrypted_payload)