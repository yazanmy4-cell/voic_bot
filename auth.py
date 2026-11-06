import aiohttp
import ssl
import random
import time
import struct as _struct
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from encrypt import enc_packet
from proto import create_proto, generate_packet, generate_packet_plain, enc_varint, decode_proto
from Pb2 import MajoRLoGinrEs_pb2, PorTs_pb2


async def fetch_version():
    url = (
        "https://version.common.redflamenco.com/live/ver.php"
        "?version=1.132.9&lang=ar&device=android&channel=android"
        "&appstore=googleplay&region=ME&release_version=OB55"
        "&whitelist_version=1.6.0&whitelist_sp_version=1.0.0"
        "&device_name=samsung%20SM-S9210"
        "&device_CPU=x86-64%20SSE3%20SSE4.1%20SSE4.2%20AVX%20AVX2"
        "&device_GPU=Adreno%20%28TM%29%20640&device_mem=1999"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    return data.get("remote_version", ""), data.get("server_url", ""), data.get("client_ip", "")
    except Exception as e:
        print(f"[VERSION]: {e}")
    return "", "", ""


async def fetch_city(ip):
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,city"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if data.get("status") == "success":
                        return data.get("city", "")
    except Exception as e:
        print(f"[GEOIP]: {e}")
    return ""


async def generate_access(uid, password, user_agent):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    data = {
        "uid": uid, "password": password, "response_type": "token", "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers={
            "Host": "100067.connect.garena.com",
            "User-Agent": user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close"
        }, data=data) as response:
            if response.status != 200:
                return None, None
            res_data = await response.json()
            return res_data.get("open_id"), res_data.get("access_token")


def build_major_login(open_id, access_token, version="1.132.9", client_ip="59.152.5.188", city="Dhaka"):
    P = {}
    P[3] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    P[4] = "free fire"
    P[5] = 1
    P[7] = version
    P[8] = "Android OS 14 / API-34 (UP1A.231005.007/V816.0.15.0.UNQMIXM)"
    P[9] = "Handheld"
    P[10] = "Grameenphone"
    P[11] = "CarrierDataNetwork"
    P[12] = 1666
    P[13] = 750
    P[14] = "352"
    P[15] = "ARM64 FP ASIMD AES | 2400 | 8"
    P[16] = 5563
    P[17] = "Mali-G57 MC2"
    P[18] = "OpenGL ES 3.2 v1.r32p1-01eac0.0a0b917d9265b4c01be9925306306139"
    P[19] = "Google|9cc73f7a-91f6-40f6-87ec-5b67e597eb8c"
    P[20] = client_ip
    P[21] = "en"
    P[22] = open_id
    P[23] = "8"
    P[24] = "Handheld"
    P[25] = "Xiaomi 2312DRAABI"
    P[26] = "BD"
    P[29] = access_token
    P[30] = 1
    P[41] = "Grameenphone"
    P[42] = "Cellular"
    P[57] = "7428b253defc164018c604a1ebbfebdf"
    P[60] = 109685
    P[61] = 58294
    P[62] = 797
    P[63] = 18000
    P[64] = 58818
    P[65] = 109685
    P[66] = 58818
    P[67] = 109685
    P[73] = 2
    P[74] = "/data/app/~~cqQgpdMykLQEM3odipXatw==/com.dts.freefireth-G6e5yOt1dtuXG5Ambhj18g==/lib/arm64"
    P[76] = 1
    P[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~cqQgpdMykLQEM3odipXatw==/com.dts.freefireth-G6e5yOt1dtuXG5Ambhj18g==/base.apk"
    P[78] = 3
    P[79] = 2
    P[81] = "64"
    P[83] = "2019121229"
    P[85] = 3
    P[86] = "OpenGLES2"
    P[87] = 4095
    P[88] = 8
    P[89] = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    P[90] = city
    P[91] = "C"
    P[92] = 8043
    P[93] = "android"
    P[94] = "KqsHT4XbSZhqerDNUhjbS3DxG/4+I62zQU2tZFJN91kBUICAlZ5yujshLKvjlk/KiShfKfis8EeB1PMhFHIodWPncZC4fCHYF3TcTwNj95aWY/S3"
    P[95] = 111207
    P[96] = '{"cur_rate":[60,90,120],"support_etc2":false}'
    P[97] = 1
    P[98] = 1
    P[99] = "4"
    P[100] = "4"
    P[102] = "GQ]        e"
    P[103] = 1
    P[104] = 45174
    P[105] = 1
    P[106] = "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a"
    P[107] = "1.9393e7b8e53e8aeb"
    return AES.new(b'Yg&tc%DEuh6%Zc^8', AES.MODE_CBC, b'6oyZDr22E3ychjM%').encrypt(pad(create_proto(P), AES.block_size))


def build_get_login_data_payload(open_id, access_token, version="1.132.9", client_ip="59.152.5.188", city="Dhaka"):
    return build_major_login(open_id, access_token, version, client_ip, city)


async def major_login(payload, headers, server_url="https://loginbp.ppmainecoonghj.com/"):
    if not server_url.startswith("http"):
        server_url = "https://" + server_url
    url = server_url.rstrip("/") + "/MajorLogin"
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers, ssl=ssl_ctx) as response:
            body = await response.read()
            print(f"[MajorLogin] status={response.status} len={len(body)}")
            if response.status == 200:
                return body
            return None


async def get_login_data(base_url, open_id, access_token, token, headers, version="1.132.9", client_ip="129.45.8.219", city="Oran"):
    if not base_url:
        print(f"[AUTH]: GetLoginData FAILED - Invalid URL")
        return None
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    url = f"{base_url}/GetLoginData"
    payload = build_get_login_data_payload(open_id, access_token, version, client_ip, city)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    current_headers = headers.copy()
    current_headers['Authorization'] = f"Bearer {token}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=payload, headers=current_headers, ssl=ssl_ctx, timeout=30) as response:
                if response.status == 200:
                    return await response.read()
                print(f"[AUTH]: GetLoginData HTTP {response.status}")
                return None
        except Exception as e:
            print(f"[AUTH]: GetLoginData Exception: {e}")
            return None


def decode_major_login(response_bytes):
    body = response_bytes
    if len(body) > 64:
        try:
            proto = MajoRLoGinrEs_pb2.MajorLoginRes()
            proto.ParseFromString(body)
            if not getattr(proto, 'token', None):
                raise ValueError("empty token")
        except Exception:
            body = body[64:]
    proto = MajoRLoGinrEs_pb2.MajorLoginRes()
    proto.ParseFromString(body)
    return proto


def decode_login_data(response_bytes):
    proto = PorTs_pb2.GetLoginData()
    proto.ParseFromString(response_bytes)
    return proto


def build_auth_startup(uid, token, timestamp, key, iv, mode="online"):
    ah = f"{int(uid):x}".zfill(16)
    enc = enc_packet(token.encode().hex(), key, iv)
    th = f"{int(timestamp):x}"
    if len(th) % 2:
        th = "0" + th
    tsz = f"{len(enc)//2:02x}"
    pad_ = "00000" if mode == "chat" else "0000000000000"
    return f"9015{ah}{th}{pad_}{tsz}{enc}"


def build_ping_packet(key, iv):
    proto_hex = create_proto({1: 15, 2: {1: 804266360, 2: 1}}).hex()
    return generate_packet(proto_hex, '0515', key, iv)


def build_join_sq(uid, code, key, iv):
    fields = {
        1: bytes.fromhex("01090a0b121619201d2729"),
        2: 40,
        3: bytes.fromhex("01090a0b121619201d2729"),
        4: "w\\Z]",
        6: 12,
        7: bytes.fromhex("01090a0b121619201d2729"),
        8: "1.132.9",
        9: 6,
        10: 2,
        11: bytes.fromhex("01090a0b121619201d2729"),
    }
    f = {
        1: 4,
        2: {
            4: bytes.fromhex("01090a0b121619201d2729"),
            5: str(code),
            6: 6,
            8: 1,
            9: fields,
            11: {1: "IDC1", 2: 99, 3: "ME"},
            13: "ar",
            16: bytes.fromhex("374f521955"),
            20: [
                {1: 3, 2: 360}, {1: 4, 2: 391}, {1: 5, 2: 156},
                {1: 29, 2: 204}, {1: 22, 2: 118}, {1: 14, 2: 139}, {1: 21},
            ],
            27: {1: 2, 2: 4},
        },
    }
    return generate_packet(create_proto(f).hex(), "0519", key, iv)


def build_ghost_msg(owner_id, bot_uid, secret_code, message, key, iv, lang="en"):
    colors = ['FF9999','99FF99','99CCFF','FFD700','FFB6C1','FFA07A','98FB98','E6E6FA','AFEEEE','F0E68C','FFE4B5','D8BFD8','FFFACD','87CEFA','FFDEAD','B0E0E6','FFDAB9','E0FFFF','F5DEB3','FFC0CB','FFF0F5','ADD8E6']
    color = random.choice(colors)
    fields = {
        1: 61,
        2: {
            1: int(owner_id),
            2: {
                1: int(owner_id),
                2: 1159,
                3: f"[b][c][{color}]{message}",
                5: 12,
                6: 9999,
                7: 1,
                8: {2: 1, 3: 1},
                9: 3,
                10: lang,
            },
            3: secret_code,
        },
    }
    return generate_packet(create_proto(fields).hex(), '0519', key, iv)


def build_leave_team(uid, key, iv):
    fields = {1: 7, 2: {1: 0}}
    return generate_packet(create_proto(fields).hex(), '0519', key, iv)


def build_sned_msg(bot_uid, target_uid, message, key, iv):
    fields = {
        1: int(bot_uid),
        2: int(target_uid),
        3: 2,
        4: message,
        5: int(time.time()),
        7: 2,
        9: {
            1: "xBesTo - C4",
            2: 902000306,
            3: 901048018,
            4: 330,
            5: 909000014,
            8: "xBesTo - C4",
            10: 1,
            11: 1,
            13: {1: 2, 2: 1},
            14: {1: 1158053040, 2: 8, 3: "\u0010\u0015\b\n\u000b\u0015\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"}
        },
        10: "en",
        13: {2: 1, 3: 1},
        14: {},
    }
    return generate_packet(create_proto(fields).hex(), '1215', key, iv)


def build_spam_invite(bot_uid, target_uid, key, iv):
    vals = [1048576, 32768, 2048, 64, 11233, 262144]
    r = random.choice(vals)
    fields = {
        1: 33,
        2: {
            1: int(target_uid),
            2: "ME", 3: 1, 4: 1, 6: "yyt", 7: 330, 8: 1000,
            9: 100, 10: "DZ", 12: 1, 13: int(target_uid), 16: 1,
            17: {2: 159, 4: "y[WW", 6: 11, 8: "1.132.9", 9: 3, 10: 1},
            18: 306, 19: 18, 24: 902027027,
            26: {},
            27: {1: 11, 2: int(bot_uid), 3: 1000},
            28: {},
            31: {1: 1, 2: r},
            32: r,
            34: {
                1: int(bot_uid), 2: 8,
                3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"
            },
        },
    }
    return generate_packet(create_proto(fields).hex(), '0519', key, iv)


def build_accept_invite(owner_uid, code, key, iv):
    fields = {
        1: 4,
        2: {
            1: int(owner_uid), 3: int(owner_uid),
            4: bytes.fromhex("01030407090a0b1216191a201d27"), 8: 1,
            9: {
                1: "088ED288AA30EE9402010100000000120013000100000001B8B110CD0F0000004676251400000000000000000000000000000000000000ff00000000cacfa16d",
                2: 53, 4: "~[YP", 6: 11, 8: "1.132.9", 9: 6, 10: 2
            },
            10: str(code),
            11: [{1: "IDC1", 2: 68, 3: "ME"}, {1: "IDC2", 2: 25, 3: "ME"}],
            13: "ar", 16: bytes.fromhex("374f5219"),
            20: [{1: 3, 2: 357}, {1: 4, 2: 385}, {1: 5, 2: 156},
                 {1: 29, 2: 204}, {1: 22, 2: 115}, {1: 14, 2: 139}, {1: 21}],
        }
    }
    return generate_packet(create_proto(fields).hex(), '0515', key, iv)


_VOICE_BASE_HEX = (
    '0a8e01' '0811100b180122' '04534f4e59' '2a013930cc80868c02'
    '3a0b61726d65616269' '2d763761' '4200'
    '4a2438323934386166322d313737392d346438372d613864352d356237363962376365623934'
    '522a464644353846423446373646363438433241354532314542434641334141453831423443394237443937'
    '5a05766f696365' '62075851' '2d42453432' '6802' '720471636f6d' '100b'
)


def build_voice_auth(uid, region_id, voice_port, region_prefix="ME"):
    base = bytearray(bytes.fromhex(_VOICE_BASE_HEX))
    base[4] = 0x07
    device_id = "FFD58FB4F76F648C2A5E21EBCFA3AAE81B4C9B7D97"
    region_str = f"{region_prefix}_{region_id}"
    field2_str = (device_id + region_str).encode()
    uid_b = uid.encode()
    field2_len = len(field2_str)
    field2_len_varint = bytes([field2_len]) if field2_len < 128 else bytes([0x80 | (field2_len & 0x7F), field2_len >> 7])
    payload = (bytes(base) + b'\x12' + field2_len_varint + field2_str +
               bytes.fromhex('20052801' '30d008' '380040005001') +
               b'\x5a' + bytes([len(uid_b)]) + uid_b + bytes.fromhex('60007000800101'))
    return _struct.pack('>I', len(payload)) + payload


def build_voice_ping(uid, region_id, voice_port, session_id=0x0b):
    base = bytearray(bytes.fromhex(_VOICE_BASE_HEX))
    base[4] = 0x09
    base_bytes = bytes(base[:-2])
    payload = base_bytes + b'\x10' + enc_varint(session_id)
    return _struct.pack('>I', len(payload)) + payload


_VOICE_CUSTOM_MAGIC = bytes.fromhex('feffffff04b50001')


def build_voice_custom(uid, region_id, uuid="f687ba460e-9b6b8bc39",
                       device_id="F76F648CCFA3AAE897", mcu_ip="0.0.0.0", region_prefix="ME"):
    uid_str = uid.zfill(11)
    uid_last3 = uid_str[-3:].encode()
    region_str = f"{region_prefix}_{region_id}".encode()
    ts = int(time.time()) & 0xFFFFFFFF
    pkt = bytearray()
    pkt.extend(_VOICE_CUSTOM_MAGIC)
    pkt.extend(b'\x00\x24'); pkt.extend(uuid.encode()); pkt.append(0)
    pkt.extend(b'\x00\x2a'); pkt.extend(device_id.encode()); pkt.append(0)
    pkt.extend(b'\x00\x1a'); pkt.extend(region_str); pkt.append(0)
    pkt.extend(b'\x00\x0b'); pkt.extend(uid_last3); pkt.extend(b'\x00\x00\x00\x00')
    pkt.extend(b'\x28\x2e\x30\x00')
    pkt.append(0x07); pkt.extend(b"0.0.0.0"); pkt.extend(b'\x00')
    pkt.append(0x0d); pkt.extend(mcu_ip.encode()); pkt.extend(b'\x00')
    pkt.extend(b'\x17\x76'); pkt.extend(_struct.pack('>I', ts)); pkt.extend(b'\x00\x00\x00\x00')
    return _struct.pack('>I', len(pkt)) + bytes(pkt)


def build_voice_redirect(uid, region_id, region_prefix="ME", ext_region="me"):
    device_id = "FFD58FB4F76F648C2A5E21EBCFA3AAE81B4C9B7D97"
    field1 = (device_id + f"{region_prefix}_{region_id}").encode()
    base = bytes.fromhex(_VOICE_BASE_HEX)
    inner = bytearray(base[3:3+142]); inner[1] = 0x11
    ext_b = ext_region.encode()
    payload = bytearray()
    payload.append(0x0a); payload.append(len(field1)); payload.extend(field1)
    payload.append(0x12); payload.append(0x8e); payload.append(0x01); payload.extend(inner)
    payload.append(0x18); payload.append(0x02)
    payload.append(0x22); payload.append(len(ext_b)); payload.extend(ext_b)
    return _struct.pack('>I', len(payload)) + bytes(payload)


def build_chat_auth(uid, region_id, key, iv):
    fields = {1: 3, 2: {1: int(uid), 3: 'en', 4: str(region_id)}}
    return generate_packet(create_proto(fields).hex(), '1215', key, iv)


async def get_random_avatar():
    return random.choice([902000068, 902000016, 902000011, 902000084, 902000085, 902000087, 902000106, 902045016])


async def build_chat_message(uid, owner_uid, message, timestamp, key, iv):
    fields = {
        1: 1,
        2: {
            1: uid, 2: owner_uid, 4: message, 5: timestamp, 7: 6,
            9: {
                1: "YAZAN", 2: await get_random_avatar(), 3: 901000029, 4: 330,
                5: 801043518, 7: 2, 10: 1, 12: 0, 13: {1: 2}, 13: "",
                14: {1: uid, 2: 8, 3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"}
            },
            10: "en", 13: {3: 1}, 14: "",
        }
    }
    return generate_packet(create_proto(fields).hex(), '1215', key, iv)


def build_chat_close(uid, key, iv):
    fields = {1: 4, 2: {1: uid, 3: "en"}}
    return generate_packet(create_proto(fields).hex(), '1215', key, iv)


def build_emote(bot_uid, target_uid, emote_id, key, iv):
    fields = {
        1: 21,
        2: {
            1: 804266360,
            2: 909000001,
            5: {
                1: int(target_uid),
                3: int(emote_id),
            },
        },
    }
    return generate_packet(create_proto(fields).hex(), '0515', key, iv)


def build_evo_packet(bot_uid, display_name, sub_type, key, iv, custom_name, evo_id):
    weapon = random.choice([907194203, 907194103, 907193603])
    name = custom_name if custom_name else ""
    field8_value = (
        '{"SkinId":' + str(weapon) + ',"Name":"' + name +
        '","Counter":0,"HasKillCountRight":false,"type":"EVOGunShare"}'
    )
    f9 = b"\x10\x15\x08\x0a\x0b\x13\x0c\x0f\x11\x04\x07\x02\x03\x0d\x0e\x12\x01\x05\x06"
    fields = {
        1: 1,
        2: {
            1: int(bot_uid),
            2: int(evo_id),
            3: 5,
            5: int(time.time()),
            7: 1,
            8: field8_value,
            9: {
                1: display_name or "",
                2: random.choice([902000063, 902000068, 902000305, 902000307, 902028006, 902034023, 902039014, 902048021, 902053018, 902048004, 902052004, 902000018]),
                3: 901053013,
                4: 330,
                5: 827001007,
                10: 1,
                11: 1,
                13: {1: 2},
                14: {1: int(bot_uid), 3: f9},
            },
            10: "tr",
            13: {2: 1, 3: 1},
            14: b"",
        },
    }
    return generate_packet(create_proto(fields).hex(), '120c', key, iv)


def build_create_squad(region, version, key, iv):
    fields = {
        1: 1,
        2: {
            2: bytes.fromhex("010304161d"), 3: 15, 4: 3, 5: "en",
            8: [{1: "IDC1", 2: 80, 3: region}, {1: "IDC2", 2: 53, 3: region},
                {1: "IDC3", 2: 124, 3: region}, {1: "IDC4", 2: 233, 3: region}],
            9: 1, 10: bytes.fromhex("01030407090a0b121619201d27"), 11: 1, 13: 1,
            14: {
                1: "08FFF3BE913CA75B02052F0222220000009600020094003C3A33107913D91078467625141101040ff77f2020ca3ca4f969cbc4e50000004f0e0e0801cacfa16d",
                2: 476,
                4: "zW\\R", 6: 11, 7: bytes.fromhex("147204676c64621613"),
                8: version, 9: 3, 10: 2,
                11: "\x03bbSQ62iz591xAdV2KyoVlTtsUZkv08Zr7Qr3yXm7+zu4THgJA8epXNyEzy1ySZuypve2AhTz0XL1xQmE0f+gIBTN1dT5v3FFqy/GNyxyaVBm6o9+4/7rXepN29ERNRafz9Ke5spj1yt7bIV3/g/x5KKpfAQAiWKJmwgKSGHu2kOkH8koNaqLmO9m8+4LPzA9HaqzDbdLM1FZiGEIvVcZYBb5zW+lexeMkXPFPX62d1kOEBVy7/+DEKJUIIUoiyxGiPgZphr8JOpmYj65gOaIlnteZHAykqwuxeVNu8Y3UTGpjzalKkDaVY7YUBctOH8wGrrH+5WybIdXDGLrmjR5k3QzG6s3hkNGAOoeAGg1hWWQCsMMduk3dQvx1TI3nIpU77TV5WRz9Hgs5qgQr8deHPnAGdXYu3kehknt44WuRavs3PCsq+ylc2/n0IIGzeWfXfMiE5cUaQ/mqocMmUBYA9gBQGjPE+uTVcCM0h+a0OUqwQma5kCWUPoZ++ZFBGgMZYOxT8QWz2r7yvG+bghm2IjuHZRm0sh2XdkPjLrTfYRy3qdBGt8CRkmaBF55/bzmvNewX8obZtriQ0sZxnnhcDYjbx2M",
            },
            19: 324, 21: bytes.fromhex("374f5219"),
            24: [{1: 3, 2: 391}, {1: 4, 2: 385}, {1: 5, 2: 192},
                 {1: 29, 2: 204}, {1: 22, 2: 115}, {1: 14, 2: 175}, {1: 21}],
            27: {7: 51},
        },
    }
    return generate_packet(create_proto(fields).hex(), '0515', key, iv)


def build_change_squad_size(grp_to, key, iv):
    fields = {1: 17, 2: {1: 6728454010, 2: 1, 3: grp_to - 1, 4: 15, 5: "\x01\x03\x04\x16\x1d", 8: 1}}
    return generate_packet(create_proto(fields).hex(), '0515', key, iv)


def build_squad_info_request(bot_uid, key, iv):
    return generate_packet(create_proto({1: 15, 2: {1: int(bot_uid), 2: 1}}).hex(), '0515', key, iv)


async def build_dm_message(bot_uid, target_uid, message, key, iv):
    fields = {
        1: 1,
        2: {
            1: int(bot_uid), 2: int(target_uid), 3: 2, 4: message, 5: int(time.time()),
            7: 6,
            9: {1: "YAZAN", 2: await get_random_avatar(), 4: 330, 5: 910050002,
                13: {}, 14: {1: int(bot_uid), 3: {}}, 18: {1: int(bot_uid), 3: 1, 4: {}}},
            10: "en", 13: {2: 1, 3: 1}, 14: {},
        },
    }
    return generate_packet(create_proto(fields).hex(), '1215', key, iv)


async def equip_emote(jwt_token, login_url=None):
    base = (login_url or "https://clientbp.ppmainecoonghj.com").rstrip("/")
    url = f"{base}/ChooseEmote"
    host = base.split("//", 1)[-1].split("/", 1)[0]
    headers = {
        "Accept-Encoding": "gzip",
        "Authorization": f"Bearer {jwt_token}",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "Host": host,
        "ReleaseVersion": "OB55",
        "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "X-GA": "v1 1",
        "X-Unity-Version": "2022.3.47f1",
    }
    data = bytes.fromhex("673b1ad08072c36b91c0749256091802")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, data=data, ssl=ctx, timeout=8) as r:
                return r.status == 200
    except Exception:
        return False


async def claim_avatar_proficiency_award(jwt_token, client_url):
    if not client_url.endswith("/"):
        client_url += "/"
    host = client_url.replace("https://", "").replace("http://", "").split("/")[0]
    payload = create_proto({1: 102000007, 2: 1})
    enc = bytes.fromhex(enc_packet(payload.hex(), b'Yg&tc%DEuh6%Zc^8', b'6oyZDr22E3ychjM%'))
    headers = {
        "User-Agent": "UnityPlayer/2018.4.12f1",
        "Authorization": f"Bearer {jwt_token}",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Host": host,
        "Content-Length": str(len(enc)),
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(client_url + "ClaimAvatarProficiencyAward", data=enc, headers=headers, ssl=ctx, timeout=12) as r:
                body = await r.read()
                print("=" * 60)
                print(f"[ClaimAvatar] status={r.status} len={len(body)}")
                print(f"[ClaimAvatar] body_hex={body.hex()}")
                award_id = None
                try:
                    parsed = decode_proto(body)
                    print(f"[ClaimAvatar] parsed={parsed}")
                    root = parsed.get('1')
                    if isinstance(root, dict):
                        f2 = root.get('2')
                        if isinstance(f2, list):
                            f2 = f2[0]
                        if isinstance(f2, dict):
                            award_id = f2.get('1')
                except Exception as e:
                    print(f"[ClaimAvatar] parse error: {e}")
                print("=" * 60)
                return r.status == 200, award_id
    except Exception as e:
        print(f"[ClaimAvatar] error: {e}")
        return False, None


async def choose_head_pic(jwt_token, client_url, head_pic_id=102000007):
    if not client_url.endswith("/"):
        client_url += "/"
    host = client_url.replace("https://", "").replace("http://", "").split("/")[0]
    payload = create_proto({1: head_pic_id})
    enc = bytes.fromhex(enc_packet(payload.hex(), b'Yg&tc%DEuh6%Zc^8', b'6oyZDr22E3ychjM%'))
    headers = {
        "User-Agent": "UnityPlayer/2018.4.12f1",
        "Authorization": f"Bearer {jwt_token}",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Host": host,
        "Content-Length": str(len(enc)),
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(client_url + "ChooseHeadPic", data=enc, headers=headers, ssl=ctx, timeout=12) as r:
                body = await r.read()
                print(f"[ChooseHeadPic] status={r.status} len={len(body)} hex={body.hex()[:120]}")
                return r.status == 200
    except Exception:
        return False


async def spam_uid(jwt_token, login_url, target_uid, key, iv):
    base = (login_url or "https://clientbp.ppmainecoonghj.com").rstrip("/")
    url = f"{base}/GetPlayerCSRankingInfoByAccountID"
    body = bytes.fromhex(enc_packet(create_proto({1: int(target_uid)}).hex(), key, iv))
    headers = {
        "User-Agent": "UnityPlayer/2018.4.12f1",
        "Authorization": f"Bearer {jwt_token}",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "X-GA-SV": str(int(time.time())),
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, data=body, headers=headers, ssl=ctx, timeout=30) as r:
                resp_body = await r.read()
                print(f"[Spam] status={r.status} len={len(resp_body)}")
                return r.status, resp_body
    except Exception as e:
        print(f"[Spam] error: {e}")
        return None, None