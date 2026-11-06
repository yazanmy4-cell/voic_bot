import asyncio
import shutil
import sys
import struct
import time
import os
import random
import json
import aiohttp
import ssl
from utils import load_accounts, default_headers, oauth_headers, log
from auth import (
    generate_access, build_major_login, major_login, get_login_data,
    decode_major_login, decode_login_data, build_auth_startup,
    build_ping_packet, build_voice_auth, build_voice_ping,
    build_voice_custom, build_voice_redirect,
    build_chat_auth, build_chat_message, build_leave_team, build_chat_close,
    fetch_version, fetch_city, build_emote,
    build_ghost_msg, build_dm_message, build_join_sq,
    equip_emote, build_sned_msg, build_spam_invite,
    build_evo_packet, build_create_squad, build_change_squad_size,
    build_squad_info_request,
)
from network import connect_online, ping_loop, read_loop
from voice import extract_garena_voice_data
from proto import decode_proto


EMOTE_MAP = {
    "scarlet": 909039011, "tiger": 909042008, "woodpecker": 909042008,
    "dreamland": 909051003, "m60": 909051003, "xm8": 909000085,
    "devil": 909000090, "famas": 909000090, "booyahday": 909000098,
    "ump": 909000098, "m4a1": 909033001, "m4": 909033001,
    "mp40": 909040010, "100lvl": 909042007, "throne": 909000014,
    "heart": 909000045, "love": 909000045, "laugh": 909000002,
    "lol": 909000002, "ak": 909000063, "mp5": 909033002,
    "p90": 909049010, "groza": 909041005, "an94": 909035012,
    "scar": 909000068, "m1887": 909035007, "g18": 909038012,
    "thompson": 909038010, "parafal": 909045001, "namdam": 909037011,
}

EVO_IDS = [
    909039011, 909042008, 909051003, 909000085, 909000090,
    909000098, 909033001, 909040010, 909042007, 909000014,
    909000045, 909000002, 909000063,
]

LIKE_API = "https://like-api.up.railway.app/like"
INFO_API = "http://de26.spaceify.eu:26080/info"


def get_random_color():
    colors = [
        "FF0000", "00FF00", "0000FF", "FFFF00", "FF00FF", "00FFFF", "FFFFFF", "FFA500",
        "A52A2A", "800080", "808080", "C0C0C0", "FFC0CB", "FFD700", "ADD8E6",
        "90EE90", "D2691E", "DC143C", "00CED1", "9400D3", "F08080", "20B2AA", "FF1493"
    ]
    return random.choice(colors)


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "ffmpeg"),
        os.path.join(script_dir, "ffmpeg.exe"),
        os.path.join(script_dir, "bin", "ffmpeg"),
        os.path.join(script_dir, "bin", "ffmpeg.exe"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    raise FileNotFoundError(
        "ffmpeg not found. Place ffmpeg binary in ./ or ./bin/ or install ffmpeg."
    )


def ogg_opus_frames_bytes(data):
    _, frames = parse_ogg_buf(data)
    yield from frames


def parse_ogg_buf(buf):
    frames = []
    while True:
        pos = buf.find(b'OggS')
        if pos == -1:
            buf = buf[-3:] if len(buf) >= 3 else buf
            break
        if len(buf) < pos + 27:
            break
        n_segs = buf[pos + 26]
        header_end = pos + 27 + n_segs
        if len(buf) < header_end:
            break
        seg_table = buf[pos + 27: header_end]
        page_size = sum(seg_table)
        if len(buf) < header_end + page_size:
            break
        page_data = buf[header_end: header_end + page_size]
        buf = buf[header_end + page_size:]
        if page_data[:8] in (b'OpusHead', b'OpusTags'):
            continue
        off = 0
        for s in seg_table:
            frame = page_data[off: off + s]
            off += s
            if len(frame) >= 4:
                frames.append(frame)
    return buf, frames


class Bot:
    def __init__(self, uid, password):
        self.uid = uid
        self.password = password
        self.key = b'Yg&tc%DEuh6%Zc^8'
        self.iv = b'6oyZDr22E3ychjM%'
        self.token = None
        self.login_url = None
        self.timestamp = None
        self.online_ip = "98.98.162.30"
        self.online_port = 39699
        self.chat_ip = None
        self.chat_port = None
        self.voice_ip = None
        self.voice_port = None
        self.voice_region_id = None
        self.voice_chat_key = None
        self.chat_region_id = None
        self.team_owner_uid = None
        self.region_prefix = "ME"
        self.ext_region = "ME"
        self.sdk_domain = "ff.rtc.grtc.garenanow.com"
        self.writer = None
        self.voice_writer = None
        self.voice_reader = None
        self.voice_ping_task = None
        self.voice_connect_task = None
        self.chat_writer = None
        self.chat_reader = None
        self.chat_buffer = bytearray()
        self.opus_bitrate = 18000
        self.voice_f5 = 0
        self.voice_f3 = 0x13e6
        self.udp_task = None
        self.current_ogg = None
        self.track_title = ""
        self.track_total_frames = 0
        self.track_current_frame = 0
        self.progress_task = None
        self.stopped_frame = 0
        self.volume = 100
        self.mp3_paths = {
            "1": ("mp.mp3", "Veki Veki"),
            "2": ("mp2.mp3", "AKAI"),
        }
        self.pending_squad_target = None
        self.chat_sub_type = 1002

    def _c(self):
        return get_random_color()

    async def handle_tcp_data(self, data):
        buffer = bytearray(data)
        pos = 0
        while pos < len(buffer) - 5:
            length = struct.unpack('>I', buffer[pos+1:pos+5])[0]
            if 0 < length < 200000 and pos + 5 + length <= len(buffer):
                payload = bytes(buffer[pos+5:pos+5+length])
                try:
                    proto_data = decode_proto(payload)
                    if not proto_data:
                        pos += 5 + length
                        continue
                    field5 = proto_data.get('5')
                    if not self.voice_region_id and isinstance(field5, dict):
                        region_id = field5.get('17')
                        if region_id:
                            self.voice_region_id = int(region_id)
                            self.chat_region_id = int(self.voice_region_id / 256 + 0.5) * 256
                            self.team_owner_uid = int(field5.get('1', self.uid))
                            chat_key = field5.get('31')
                            if chat_key:
                                self.voice_chat_key = str(chat_key)
                            log("TEAM", f"region_id={self.voice_region_id} owner={self.team_owner_uid}")
                            asyncio.create_task(self.connect_chat())
                            if not self.voice_connect_task or self.voice_connect_task.done():
                                self.voice_connect_task = asyncio.create_task(self.voice_connect())
                    if isinstance(field5, dict):
                        sender_uid_online = str(field5.get('1', ''))
                        msg_online = field5.get('4', '')
                        if isinstance(msg_online, str) and msg_online.strip() and sender_uid_online != str(self.uid):
                            log("CHAT", f"[online][{sender_uid_online}]: {msg_online}")
                    if self.pending_squad_target:
                        sq_data = proto_data.get('5')
                        if isinstance(sq_data, dict):
                            items = sq_data if isinstance(sq_data, list) else [sq_data]
                        elif isinstance(sq_data, list):
                            items = sq_data
                        else:
                            items = []
                        for _it in items:
                            if not isinstance(_it, dict):
                                continue
                            _entry = _it
                            if '17' not in _entry or '31' not in _entry:
                                _inner = _it.get('3', {})
                                if isinstance(_inner, dict) and '17' in _inner and '31' in _inner:
                                    _entry = _inner
                            if '17' in _entry and '31' in _entry:
                                _squad_code = str(_entry.get('31', ''))
                                if '_' in _squad_code:
                                    tgt = self.pending_squad_target
                                    self.pending_squad_target = None
                                    async def send_squad_code(_code=_squad_code, _t=tgt):
                                        try:
                                            pkt = await build_dm_message(int(self.uid), int(_t),
                                                f"[b][c][{self._c()}]Team Created! Copy code:\n[FFFFFF]{_code}",
                                                self.key, self.iv)
                                            if self.chat_writer and not self.chat_writer.transport.is_closing():
                                                self.chat_writer.write(pkt)
                                                await self.chat_writer.drain()
                                        except Exception:
                                            pass
                                    asyncio.create_task(send_squad_code())
                                    break
                except Exception:
                    pass
                pos += 5 + length
            else:
                pos += 1

    async def voice_connect(self):
        if not self.voice_region_id:
            return
        self.voice_f5 = 0
        self.voice_f3 = 0x13e6
        import re as _re

        async def read_voice_frame(reader, timeout):
            header = await asyncio.wait_for(reader.readexactly(4), timeout)
            fl = struct.unpack('>I', header)[0]
            if fl <= 0 or fl > 65536:
                raise ValueError(f"invalid frame length: {fl}")
            return await asyncio.wait_for(reader.readexactly(fl), timeout)

        redirect_ip, redirect_port = None, None
        sdk_url = f"https://{self.sdk_domain}/sdk/sdk_verify"
        sdk_payload = bytes.fromhex(
            '0a8e010800100b180122074f6e65506c75732a013930cc80868c023a0961726d3634'
            '2d76386142004a2439313864346563382d383733332d343930622d626334362d643132'
            '666139396337383238522a464644353846423446373646363438433241354532314542'
            '4346413341414538314234433942374439375a05766f69636562064e45323231316802'
            '720471636f6d12800160ad4251d2f821e2701e5e1d8b607d2b34dcb0c512300ac3e5839'
            '6155780dc64686b20d05581c038ae28539fc3bc21ced330e31721e18e6c626972829f'
            '6878cb8ec7d95f2f7391bd25f9d7296f09f56f9bc5bccabaf10f09b58c39dc02c08995'
            'd6abe727d93bcea4123da86ad42f6500fa68e74ddc2ed2cb7af0aadd22d2ec93180120'
            '063800'
        )

        def parse_sdk(data):
            nonlocal redirect_ip, redirect_port
            if len(data) < 4:
                return
            vp = decode_proto(data)
            f5 = vp.get('5')
            cands = f5 if isinstance(f5, list) else ([f5] if f5 else [])
            for r in cands:
                if isinstance(r, bytes):
                    r = decode_proto(r)
                if isinstance(r, dict):
                    rip, rport = r.get('1'), r.get('2')
                    if isinstance(rip, str) and '.' in rip and rport:
                        redirect_ip, redirect_port = rip, int(rport)
                        break
            if not redirect_ip:
                m = _re.search(rb'([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})', data)
                if m:
                    redirect_ip = m.group(1).decode()

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            async with aiohttp.ClientSession() as sess:
                async with sess.post(sdk_url, data=sdk_payload, headers={
                    "Host": self.sdk_domain, "Accept": "*/*", "Accept-Encoding": "identity",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Content-Length": str(len(sdk_payload)),
                }, ssl=ctx, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    body = await resp.read()
                    if resp.status == 200 and len(body) > 4:
                        parse_sdk(body)
        except Exception:
            pass

        if not redirect_ip or not redirect_port:
            return
        try:
            r2, w2 = await asyncio.wait_for(asyncio.open_connection(redirect_ip, redirect_port), timeout=5.0)
        except Exception:
            return
        w2.write(build_voice_redirect(self.uid, self.voice_region_id, self.region_prefix, self.ext_region))
        await w2.drain()
        voice_ip, voice_port = None, None
        try:
            header2 = await asyncio.wait_for(r2.readexactly(4), timeout=5.0)
            rl = struct.unpack('>I', header2)[0]
            if 0 < rl < 65536:
                resp2 = header2 + await asyncio.wait_for(r2.readexactly(rl), timeout=5.0)
                proto = decode_proto(resp2[4:])
                ip_val, port_val = proto.get('1'), proto.get('2')
                if isinstance(ip_val, str) and '.' in ip_val:
                    voice_ip = ip_val
                if isinstance(port_val, int):
                    voice_port = port_val
        except asyncio.TimeoutError:
            pass
        w2.close()
        if not voice_ip or not voice_port:
            return
        try:
            r3, w3 = await asyncio.wait_for(asyncio.open_connection(voice_ip, voice_port), timeout=5.0)
        except Exception:
            return
        self.voice_writer = w3
        self.voice_reader = r3
        auth3 = build_voice_auth(self.uid, self.voice_region_id, voice_port, self.region_prefix)
        w3.write(auth3[:4]); await w3.drain()
        w3.write(auth3[4:]); await w3.drain()
        try:
            resp3 = await read_voice_frame(r3, 3.0)
            if resp3:
                p = decode_proto(resp3)
                self.voice_f3 = int(p.get('3', 0x13e6))
                f5v = p.get('5', p.get('13', 0))
                if isinstance(f5v, dict): f5v = f5v.get('1', 0)
                if isinstance(f5v, list): f5v = f5v[0] if f5v else 0
                self.voice_f5 = int(f5v) & 0xFFFFFFFF
        except (asyncio.TimeoutError, TypeError, ValueError):
            pass
        if self.voice_f5 == 0:
            try: w3.close(); await w3.wait_closed()
            except: pass
            self.voice_writer = None
            self.voice_reader = None
            await asyncio.sleep(3)
            self.voice_connect_task = asyncio.create_task(self.voice_connect())
            return
        custom = build_voice_custom(self.uid, self.voice_region_id, mcu_ip=voice_ip, region_prefix=self.region_prefix)
        w3.write(custom[:4]); await w3.drain()
        w3.write(custom[4:]); await w3.drain()
        try:
            await read_voice_frame(r3, 3.0)
        except asyncio.TimeoutError:
            pass
        if self.voice_ping_task:
            self.voice_ping_task.cancel()
        self.voice_ping_task = asyncio.create_task(self.voice_ping_loop(w3, r3))
        self.voice_ip = voice_ip
        self.voice_port = voice_port
        log("VOICE", f"Streaming to {voice_ip}:{voice_port+2}")

    async def voice_ping_loop(self, writer, reader):
        try:
            while writer and not writer.transport.is_closing():
                await asyncio.sleep(5)
                try:
                    writer.write(build_voice_ping(self.uid, self.voice_region_id, self.voice_port, self.voice_f3))
                    await writer.drain()
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    async def leave_team(self):
        log("TEAM", "Leaving...")
        if self.writer:
            self.writer.write(build_leave_team(int(self.uid), self.key, self.iv))
            await self.writer.drain()
        if self.chat_writer:
            try:
                self.chat_writer.write(build_chat_close(int(self.uid), self.key, self.iv))
                await self.chat_writer.drain()
            except Exception:
                pass
        for t in (self.udp_task, self.progress_task, self.voice_ping_task, self.voice_connect_task):
            if t and not t.done():
                t.cancel()
        self.voice_region_id = None
        self.chat_region_id = None
        self.team_owner_uid = None
        self.voice_chat_key = None
        self.voice_ip = None
        self.voice_port = None
        self.voice_writer = None
        self.voice_reader = None
        self.current_ogg = None
        self.track_title = ""
        self.track_total_frames = 0
        self.track_current_frame = 0
        self.stopped_frame = 0
        log("TEAM", "Left.")

    async def connect_chat(self):
        if not self.chat_writer or self.chat_writer.transport.is_closing():
            return
        if not self.voice_region_id:
            return
        try:
            owner = self.team_owner_uid if self.team_owner_uid else int(self.uid)
            self.chat_writer.write(build_chat_auth(owner, str(self.chat_region_id), self.key, self.iv))
            await self.chat_writer.drain()
        except Exception as e:
            log("CHAT", f"Chat auth failed: {e}")

    async def send_chat_message(self, message):
        if not self.chat_writer:
            return
        try:
            owner = self.team_owner_uid if self.team_owner_uid else int(self.uid)
            pkt = await build_chat_message(int(self.uid), owner, message, int(time.time()), self.key, self.iv)
            self.chat_writer.write(pkt)
            await self.chat_writer.drain()
        except Exception as e:
            log("CHAT", f"Send error: {e}")

    async def chat_read_loop(self, reader):
        try:
            while True:
                data = await reader.read(16384)
                if not data:
                    break
                await self.handle_chat_data(data)
        except Exception:
            pass

    async def chat_keepalive_loop(self, writer):
        try:
            while writer and not writer.transport.is_closing():
                await asyncio.sleep(5)
                try:
                    writer.write(bytes.fromhex('0201'))
                    await writer.drain()
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    async def handle_chat_data(self, data):
        self.chat_buffer.extend(data)
        buffer = self.chat_buffer
        pos = 0
        while len(buffer) - pos >= 5:
            length = struct.unpack('>I', buffer[pos+1:pos+5])[0]
            if 0 < length < 200000 and pos + 5 + length <= len(buffer):
                payload = bytes(buffer[pos+5:pos+5+length])
                try:
                    proto_data = decode_proto(payload)
                    if proto_data:
                        field5 = proto_data.get('5')
                        if isinstance(field5, dict):
                            sub = field5.get('1')
                            if sub and 1000 <= sub <= 1010:
                                self.chat_sub_type = int(sub)
                            sender_uid = str(field5.get('1', ''))
                            message = field5.get('4', '')
                            msg_type = field5.get('3', 0)
                            sender_name = ""
                            f9 = field5.get('9', {})
                            if isinstance(f9, dict):
                                sender_name = str(f9.get('1', ''))
                            if isinstance(message, str) and message.strip() and sender_uid != str(self.uid):
                                if str(msg_type) == '2':
                                    asyncio.create_task(self.handle_dm(message.strip(), sender_name, sender_uid))
                                else:
                                    asyncio.create_task(self.handle_command(message.strip(), sender_name, sender_uid))
                except Exception:
                    pass
                pos += 5 + length
            else:
                if length <= 0 or length >= 200000:
                    pos += 1
                else:
                    break
        if pos:
            del buffer[:pos]

    async def handle_dm(self, message, sender_name, sender_uid):
        try:
            msg = message.strip()
            if msg.startswith('/'):
                msg = '!' + msg[1:]
            cmd = msg.lower().split()[0] if msg else ""
            args = msg.split()[1:] if len(msg.split()) > 1 else []
            reply_target = int(sender_uid)
            async def dm_reply(text):
                try:
                    pkt = await build_dm_message(int(self.uid), reply_target, text, self.key, self.iv)
                    if self.chat_writer and not self.chat_writer.transport.is_closing():
                        self.chat_writer.write(pkt)
                        await self.chat_writer.drain()
                except Exception:
                    pass
            if cmd == "!help":
                await dm_reply(
                    f"[b][c][{self._c()}]» CoMmAnDs «\n"
                    f"[b][c][{self._c()}]!play 1 / 2\n"
                    f"[b][c][{self._c()}]!join {{code}}\n"
                    f"[b][c][{self._c()}]!5 => create squad 5\n"
                    f"[b][c][{self._c()}]!event {{name}} => EVO gun share\n"
                    f"[b][c][{self._c()}]!evo => list\n"
                    f"[b][c][{self._c()}]!evo {{name}} => equip on you\n"
                    f"[b][c][{self._c()}]!spam {{uid}}\n"
                    f"[b][c][{self._c()}]!like {{uid}}\n"
                    f"[b][c][{self._c()}]!info {{uid}}\n"
                    f"[b][c][{self._c()}]!bio {{uid}}\n"
                    f"[b][c][{self._c()}]!ghost {{code}} {{name}} {{msg}}\n"
                    f"[b][c][{self._c()}]!admin\n"
                    f"[b][c][{self._c()}]!stop / !resume\n"
                    f"[b][c][{self._c()}]!leave"
                )
            else:
                asyncio.create_task(self.handle_command(message.strip(), sender_name, sender_uid))
        except Exception as e:
            log("CMD", f"DM error: {e}")

    async def handle_command(self, message, sender_name, sender_uid):
        try:
            msg = message.strip()
            if msg.startswith('/'):
                msg = '!' + msg[1:]
            cmd = msg.lower().split()[0] if msg else ""
            args = msg.split()[1:] if len(msg.split()) > 1 else []
            log("CMD", f"recv cmd={repr(cmd)} args={args} from={sender_uid}")

            if cmd == "!help":
                help_msg = (
                    f"[b][c][{self._c()}]Hello {sender_name}\n"
                    f"[b][c][{self._c()}]» CoMmAnDs «\n"
                    f"[b][c][{self._c()}]!play 1 / 2\n"
                    f"[b][c][{self._c()}]!join {{code}}\n"
                    f"[b][c][{self._c()}]!5 => create squad 5\n"
                    f"[b][c][{self._c()}]!event {{name}} => EVO gun share\n"
                    f"[b][c][{self._c()}]!evo => list\n"
                    f"[b][c][{self._c()}]!evo {{name}} => equip on you\n"
                    f"[b][c][{self._c()}]!spam {{uid}}\n"
                    f"[b][c][{self._c()}]!like {{uid}}\n"
                    f"[b][c][{self._c()}]!info {{uid}}\n"
                    f"[b][c][{self._c()}]!bio {{uid}}\n"
                    f"[b][c][{self._c()}]!ghost {{code}} {{name}} {{msg}}\n"
                    f"[b][c][{self._c()}]!admin\n"
                    f"[b][c][{self._c()}]!stop / !resume\n"
                    f"[b][c][{self._c()}]!leave"
                )
                await self.send_chat_message(help_msg)

            elif cmd == "!play":
                if not args:
                    await self.send_chat_message(f"[b][c][{self._c()}]!play 1 => Veki Veki\n[b][c][{self._c()}]!play 2 => AKAI")
                    return
                choice = args[0].strip()
                if choice not in self.mp3_paths:
                    await self.send_chat_message(f"[b][c][{self._c()}]Invalid. Use !play 1 or !play 2")
                    return
                filename, title = self.mp3_paths[choice]
                if not os.path.exists(filename):
                    await self.send_chat_message(f"[b][c][{self._c()}]{filename} not found!")
                    return
                if not self.voice_ip or not self.voice_port:
                    await self.send_chat_message(f"[b][c][{self._c()}]Not in a team. Use !join {{code}} first.")
                    return
                await self.send_chat_message(f"[b][c][{self._c()}]Playing: {title}")
                asyncio.create_task(self._play_mp3(filename, title))

            elif cmd == "!join":
                if not args:
                    await self.send_chat_message(f"[b][c][{self._c()}]Usage: !join {{team_code}}")
                    return
                team_code = args[0].strip()
                if self.voice_region_id:
                    await self.send_chat_message(f"[b][c][{self._c()}]Bot already in team!")
                    return
                await self.send_chat_message(f"[b][c][{self._c()}]Joining {team_code}...")
                if self.writer and not self.writer.transport.is_closing():
                    self.writer.write(build_join_sq(int(self.uid), team_code, self.key, self.iv))
                    await self.writer.drain()

            elif cmd == "!5":
                size = 5
                if self.voice_region_id:
                    await self.send_chat_message(f"[b][c][{self._c()}]Bot already in team!")
                    return
                async def make_squad():
                    try:
                        if not self.writer or self.writer.transport.is_closing():
                            return
                        region = self.region_prefix
                        ver = getattr(self, 'current_version', '1.132.9')
                        self.writer.write(build_create_squad(region, ver, self.key, self.iv))
                        await self.writer.drain()
                        await asyncio.sleep(0.5)
                        self.writer.write(build_change_squad_size(size, self.key, self.iv))
                        await self.writer.drain()
                        await asyncio.sleep(0.5)
                        self.writer.write(build_squad_info_request(int(self.uid), self.key, self.iv))
                        await self.writer.drain()
                        self.pending_squad_target = str(sender_uid)
                        await self.send_chat_message(f"[b][c][{self._c()}]Squad 5 created!")
                    except Exception as e:
                        await self.send_chat_message(f"[b][c][{self._c()}]Error: {e}")
                asyncio.create_task(make_squad())

            elif cmd == "!event":
                name = args[0] if args else "YAZAN"
                evo_id = random.choice(EVO_IDS)
                sub_type = self.chat_sub_type
                async def do_event():
                    try:
                        if not self.chat_writer or self.chat_writer.transport.is_closing():
                            await self.send_chat_message(f"[b][c][{self._c()}]Chat not ready.")
                            return
                        pkt = build_evo_packet(
                            int(self.uid),
                            name,
                            sub_type,
                            self.key,
                            self.iv,
                            name,
                            evo_id,
                        )
                        self.chat_writer.write(pkt)
                        await self.chat_writer.drain()
                        await self.send_chat_message(
                            f"[b][c][{self._c()}]EVO sent! id={evo_id} name={name}"
                        )
                    except Exception as e:
                        await self.send_chat_message(f"[b][c][{self._c()}]Event error: {e}")
                asyncio.create_task(do_event())

            elif cmd == "!evo":
                if not args:
                    lines = [f"[b][c][{self._c()}]» EmOtEs «"]
                    for name in sorted(EMOTE_MAP.keys()):
                        lines.append(f"[b][c][{self._c()}]{name} => {EMOTE_MAP[name]}")
                    lines.append(f"[b][c][{self._c()}]Type: !evo {{name}} to equip on you")
                    await self.send_chat_message("\n".join(lines))
                else:
                    name = args[0].lower()
                    if name not in EMOTE_MAP:
                        await self.send_chat_message(f"[b][c][{self._c()}]Unknown emote: {name}")
                        return
                    emote_id = EMOTE_MAP[name]
                    async def do_evo():
                        try:
                            await equip_emote(self.token, self.login_url)
                            await asyncio.sleep(0.5)
                            if self.writer and not self.writer.transport.is_closing():
                                self.writer.write(build_emote(int(self.uid), int(sender_uid), emote_id, self.key, self.iv))
                                await self.writer.drain()
                                await self.send_chat_message(f"[b][c][{self._c()}]EvO {name} => {sender_uid}")
                        except Exception as e:
                            await self.send_chat_message(f"[b][c][{self._c()}]Error: {e}")
                    asyncio.create_task(do_evo())

            elif cmd == "!spam":
                if not args or not args[0].isdigit():
                    await self.send_chat_message(f"[b][c][{self._c()}]Usage: !spam {{uid}}")
                    return
                target_uid = args[0]
                async def spam_loop():
                    count = 0
                    for _ in range(10):
                        pkt = build_spam_invite(int(self.uid), int(target_uid), self.key, self.iv)
                        if self.writer and not self.writer.transport.is_closing():
                            try:
                                self.writer.write(pkt)
                                await self.writer.drain()
                                count += 1
                            except Exception:
                                pass
                        await asyncio.sleep(0.5)
                    await self.send_chat_message(f"[b][c][{self._c()}]Invite spam sent {count}/10 to {target_uid}")
                asyncio.create_task(spam_loop())

            elif cmd == "!like":
                if not args:
                    await self.send_chat_message(f"[b][c][{self._c()}]Usage: !like {{uid}}")
                    return
                target = args[0].strip()
                async def do_like():
                    try:
                        async with aiohttp.ClientSession() as s:
                            async with s.get(f"{LIKE_API}?uid={target}", timeout=30) as r:
                                if r.status == 200:
                                    d = await r.json()
                                    await self.send_chat_message(
                                        f"[b][c][{self._c()}]» Like «\n"
                                        f"[b][c][{self._c()}]Name: [FFFFFF]{d.get('Name','?')}\n"
                                        f"[b][c][{self._c()}]Before: [FFFFFF]{d.get('Like Before','?')}\n"
                                        f"[b][c][{self._c()}]After: [FFFFFF]{d.get('Like After','?')}\n"
                                        f"[b][c][{self._c()}]Added: [FFFFFF]{d.get('Likes Added','?')}"
                                    )
                                else:
                                    await self.send_chat_message(f"[b][c][{self._c()}]API error: {r.status}")
                    except Exception as e:
                        await self.send_chat_message(f"[b][c][{self._c()}]Error: {e}")
                asyncio.create_task(do_like())

            elif cmd == "!info":
                if not args:
                    await self.send_chat_message(f"[b][c][{self._c()}]Usage: !info {{uid}}")
                    return
                target = args[0].strip()
                async def do_info():
                    try:
                        async with aiohttp.ClientSession() as s:
                            async with s.get(f"{INFO_API}?uid={target}", timeout=30) as r:
                                if r.status == 200:
                                    d = await r.json()
                                    basic = d.get("basicInfo", {})
                                    await self.send_chat_message(
                                        f"[b][c][{self._c()}]» Info «\n"
                                        f"[b][c][{self._c()}]Name: [FFFFFF]{basic.get('nickname','?')}\n"
                                        f"[b][c][{self._c()}]Level: [FFFFFF]{basic.get('level','?')}\n"
                                        f"[b][c][{self._c()}]Region: [FFFFFF]{basic.get('region','?')}\n"
                                        f"[b][c][{self._c()}]Exp: [FFFFFF]{basic.get('exp','?')}\n"
                                        f"[b][c][{self._c()}]Likes: [FFFFFF]{basic.get('liked','?')}"
                                    )
                                else:
                                    await self.send_chat_message(f"[b][c][{self._c()}]API error: {r.status}")
                    except Exception as e:
                        await self.send_chat_message(f"[b][c][{self._c()}]Error: {e}")
                asyncio.create_task(do_info())

            elif cmd == "!bio":
                if not args:
                    await self.send_chat_message(f"[b][c][{self._c()}]Usage: !bio {{uid}}")
                    return
                target = args[0].strip()
                async def do_bio():
                    try:
                        async with aiohttp.ClientSession() as s:
                            async with s.get(f"{INFO_API}?uid={target}", timeout=30) as r:
                                if r.status != 200:
                                    await self.send_chat_message(f"[b][c][{self._c()}]API error: {r.status}")
                                    return
                                d = await r.json()
                        signature = d.get("signature")
                        if not signature:
                            basic = d.get("basicInfo", {})
                            signature = basic.get("signature")
                        if not signature:
                            for k, v in d.items():
                                if isinstance(v, dict) and v.get("signature"):
                                    signature = v["signature"]
                                    break
                        if not signature:
                            await self.send_chat_message(f"[b][c][{self._c()}]No signature found.")
                            return
                        name = d.get("basicInfo", {}).get("nickname", target)
                        await self.send_chat_message(
                            f"[b][c][{self._c()}]» Bio «\n"
                            f"[b][c][{self._c()}]Uid: [FFFFFF]{target}\n"
                            f"[b][c][{self._c()}]Name: [FFFFFF]{name}\n"
                            f"[b][c][{self._c()}]Bio: [FFFFFF]{signature}"
                        )
                    except Exception as e:
                        await self.send_chat_message(f"[b][c][{self._c()}]Error: {e}")
                asyncio.create_task(do_bio())

            elif cmd == "!ghost":
                if len(args) < 3:
                    await self.send_chat_message(f"[b][c][{self._c()}]Usage: !ghost {{team_code}} {{name}} {{msg}}")
                    return
                gc = args[0]
                gn = args[1]
                gm = " ".join(args[2:])
                async def do_ghost():
                    try:
                        if not self.writer or self.writer.transport.is_closing():
                            return
                        self.writer.write(build_join_sq(int(self.uid), gc, self.key, self.iv))
                        await self.writer.drain()
                        await asyncio.sleep(1.0)
                        for _ in range(3):
                            self.writer.write(build_ghost_msg(int(self.uid), int(self.uid), gc, f"{gn} {gm}", self.key, self.iv))
                            await self.writer.drain()
                            await asyncio.sleep(0.01)
                        await asyncio.sleep(0.3)
                        self.writer.write(build_leave_team(int(self.uid), self.key, self.iv))
                        await self.writer.drain()
                        await self.send_chat_message(f"[b][c][{self._c()}]Ghost sent x3 + Exit")
                    except Exception:
                        await self.send_chat_message(f"[b][c][{self._c()}]Error")
                asyncio.create_task(do_ghost())

            elif cmd == "!admin":
                await self.send_chat_message(
                    f"[b][c][{self._c()}]» Admin «\n"
                    f"[b][c][{self._c()}]YAZAN\n"
                    f"[b][c][{self._c()}]@xi4zan"
                )

            elif cmd == "!stop":
                if self.udp_task and not self.udp_task.done():
                    self.udp_task.cancel()
                    if self.progress_task and not self.progress_task.done():
                        self.progress_task.cancel()
                    self.stopped_frame = self.track_current_frame
                    elapsed_s = int(self.stopped_frame * 0.02)
                    total_s = int(self.track_total_frames * 0.02)
                    await self.send_chat_message(
                        f"[b][c][{self._c()}]Stopped at {elapsed_s//60}:{elapsed_s%60:02d} / {total_s//60}:{total_s%60:02d}\n"
                        f"[b][c][{self._c()}]{self.track_title}\n"
                        f"[b][c][{self._c()}]Use !resume to continue."
                    )
                else:
                    await self.send_chat_message(f"[b][c][{self._c()}]Nothing is playing.")

            elif cmd == "!resume":
                if self.current_ogg and self.voice_ip:
                    sf = getattr(self, 'stopped_frame', 0)
                    await self.send_chat_message(f"[b][c][{self._c()}]Resuming: {self.track_title}")
                    self.udp_task = asyncio.create_task(
                        self.voice_udp_loop(self.voice_ip, self.voice_port, ogg_data=self.current_ogg, start_frame=sf)
                    )
                    if self.progress_task and not self.progress_task.done():
                        self.progress_task.cancel()
                    self.progress_task = asyncio.create_task(self.auto_progress_loop())
                else:
                    await self.send_chat_message(f"[b][c][{self._c()}]Nothing to resume.")

            elif cmd in ("/leave", "!leave"):
                await self.leave_team()

        except Exception as e:
            import traceback
            log("CHAT", f"Command error: {e} | {traceback.format_exc()[-200:]}")

    async def _play_mp3(self, filename, title):
        try:
            if not self.voice_ip or not self.voice_port:
                await self.send_chat_message(f"[b][c][{self._c()}]Voice not ready.")
                return
            if self.udp_task and not self.udp_task.done():
                self.udp_task.cancel()
                await asyncio.sleep(0.5)
            with open(filename, "rb") as f:
                mp3_data = f.read()
            if not mp3_data:
                await self.send_chat_message(f"[b][c][{self._c()}]{filename} is empty!")
                return
            ogg_data = await self._encode_mp3_to_opus(mp3_data)
            if not ogg_data:
                await self.send_chat_message(f"[b][c][{self._c()}]Encoding failed.")
                return
            self.current_ogg = ogg_data
            self.track_title = title
            frames = list(ogg_opus_frames_bytes(ogg_data))
            self.track_total_frames = len(frames)
            self.track_current_frame = 0
            self.udp_task = asyncio.create_task(
                self.voice_udp_loop(self.voice_ip, self.voice_port, ogg_data=ogg_data)
            )
            if self.progress_task and not self.progress_task.done():
                self.progress_task.cancel()
            self.progress_task = asyncio.create_task(self.auto_progress_loop())
            await self.send_chat_message(f"[b][c][{self._c()}]Now Playing: {title}")
        except Exception as e:
            await self.send_chat_message(f"[b][c][{self._c()}]Play error: {e}")

    async def _encode_mp3_to_opus(self, mp3_data):
        import subprocess
        import tempfile as tmp
        loop = asyncio.get_event_loop()

        def _run():
            mp3_p = tmp.mktemp(suffix='.mp3')
            opus_p = tmp.mktemp(suffix='.ogg')
            try:
                with open(mp3_p, 'wb') as f:
                    f.write(mp3_data)
                subprocess.run([
                    ffmpeg_exe(), "-loglevel", "quiet", "-y",
                    "-i", mp3_p,
                    "-ar", "16000",
                    "-ac", "1",
                    "-af", f"volume={self.volume/100.0},loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-c:a", "libopus",
                    "-b:a", f"{self.opus_bitrate}",
                    "-frame_duration", "20",
                    "-application", "voip",
                    "-f", "ogg",
                    opus_p
                ], check=True)
                with open(opus_p, 'rb') as f:
                    return f.read()
            finally:
                for p in (mp3_p, opus_p):
                    try: os.unlink(p)
                    except: pass

        return await loop.run_in_executor(None, _run)

    async def auto_progress_loop(self):
        try:
            await asyncio.sleep(15)
            while self.udp_task and not self.udp_task.done():
                if self.track_total_frames > 0:
                    frame = self.track_current_frame
                    total = self.track_total_frames
                    elapsed_s = int(frame * 0.02)
                    total_s = int(total * 0.02)
                    pct = min(frame / total, 1.0)
                    bar_len = 16
                    filled = int(bar_len * pct)
                    bar = f"[b][c][{self._c()}]" + "\u25a0" * filled + "\u25a1" * (bar_len - filled)
                    elapsed_str = f"{elapsed_s//60}:{elapsed_s%60:02d}"
                    total_str = f"{total_s//60}:{total_s%60:02d}"
                    await self.send_chat_message(
                        f"[b][c][{self._c()}]\u25b6 {self.track_title[:38]}\n"
                        f"{bar}\n"
                        f"[b][c][{self._c()}]{elapsed_str} / {total_str}  Vol:{self.volume}%"
                    )
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    async def voice_udp_loop(self, ip, port, ogg_data=None, start_frame=0):
        import socket as _sock
        udp_port = port + 2
        if not ogg_data:
            return
        frames = list(ogg_opus_frames_bytes(ogg_data))
        converted = []
        for f in frames:
            if f[0] == 0x78:
                continue
            if f[0] == 0x4b and len(f) > 2 and f[1] == 0x01:
                converted.append(bytes([0x48]) + f[2:])
            else:
                converted.append(f)
        frames = converted
        udp = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        magic = b'\x41\x6f'
        seq = random.randint(0, 0xFFFF)
        ts = random.randint(0, 0xFFFFFFFF)
        FRAME_SAMPLES = 0x3c0
        FRAME_DURATION = 0.020
        f3_val = getattr(self, 'voice_f3', 0x13e6)
        FIXED_2 = b'\x00\x00' + f3_val.to_bytes(2, 'big')
        mic_open = b'\x71\x5c\x35\x07\x00\x00\x00\x00\x80\x02\x00\x00\x00\x00' + f3_val.to_bytes(2, 'big')
        udp.setblocking(False)
        loop = asyncio.get_running_loop()

        async def udp_receiver():
            try:
                while True:
                    await loop.sock_recvfrom(udp, 4096)
            except asyncio.CancelledError:
                pass
            except (ConnectionError, OSError):
                pass

        udp_rx_task = asyncio.create_task(udp_receiver())
        try:
            udp.sendto(mic_open, (ip, udp_port))
        except OSError:
            pass
        try:
            while True:
                seq_loop = seq
                ts_loop = ts
                loop_start = start_frame if seq_loop == seq else 0
                self.track_current_frame = loop_start
                next_send = time.monotonic()
                for i in range(loop_start, len(frames)):
                    opus_frame = frames[i]
                    f5_val = getattr(self, 'voice_f5', 0)
                    FIXED_1 = f5_val.to_bytes(4, 'big')
                    header = struct.pack('>2sHI4s4s', magic, seq_loop & 0xFFFF, ts_loop & 0xFFFFFFFF, FIXED_1, FIXED_2)
                    try:
                        udp.sendto(header + opus_frame, (ip, udp_port))
                    except Exception:
                        pass
                    self.track_current_frame = i
                    seq_loop = (seq_loop + 1) & 0xFFFF
                    ts_loop = (ts_loop + FRAME_SAMPLES) & 0xFFFFFFFF
                    next_send += FRAME_DURATION
                    sleep_time = next_send - time.monotonic()
                    if sleep_time > 0:
                        try:
                            await asyncio.sleep(sleep_time)
                        except asyncio.CancelledError:
                            self.stopped_frame = i
                            raise
                seq = seq_loop
                ts = ts_loop
                start_frame = 0
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        finally:
            udp_rx_task.cancel()
            try:
                await udp_rx_task
            except asyncio.CancelledError:
                pass
            udp.close()

    async def run(self):
        log("AUTH", f"Logging in {self.uid}...")
        headers = default_headers()
        oauth_h = oauth_headers()
        current_version, server_url, client_ip = await fetch_version()
        if not current_version:
            current_version = "1.132.9"
        if not server_url:
            server_url = "https://loginbp.ppmainecoonghj.com/"
        if not client_ip:
            client_ip = "129.45.8.219"
        self.current_version = current_version
        city = await fetch_city(client_ip)
        if not city:
            city = "Oran"
        open_id, access_token = await generate_access(self.uid, self.password, oauth_h['User-Agent'])
        if not open_id:
            log("AUTH", "OAuth Failed")
            return
        major_payload = build_major_login(open_id, access_token, version=current_version, client_ip=client_ip, city=city)
        major_resp = await major_login(major_payload, headers, server_url=server_url)
        if not major_resp:
            log("AUTH", "MajorLogin Failed")
            return
        major_proto = decode_major_login(major_resp)
        raw_p = decode_proto(major_resp)
        self.token = getattr(major_proto, 'token', None) or raw_p.get('8') or None
        self.login_url = getattr(major_proto, 'url', None) or raw_p.get('10') or None
        proto_ts = getattr(major_proto, 'timestamp', None) or raw_p.get('21')
        self.timestamp = int(proto_ts) if proto_ts else int(time.time())
        account_uid = getattr(major_proto, 'account_uid', None) or raw_p.get('1')
        if account_uid:
            self.uid = str(account_uid)
        new_key = getattr(major_proto, 'key', None) or (raw_p.get('22') if isinstance(raw_p.get('22'), bytes) else None)
        new_iv = getattr(major_proto, 'iv', None) or (raw_p.get('23') if isinstance(raw_p.get('23'), bytes) else None)
        if new_key and len(new_key) == 16:
            self.key = new_key
        if new_iv and len(new_iv) == 16:
            self.iv = new_iv
        login_data_resp = await get_login_data(self.login_url, open_id, access_token, self.token, headers, version=current_version, client_ip=client_ip, city=city)
        if not login_data_resp:
            log("AUTH", "GetLoginData Failed")
            return
        voice_data = extract_garena_voice_data(login_data_resp)
        for entry in voice_data["idc_servers"]:
            parts = entry['ip_port'].split(':')
            ip, port = parts[0], int(parts[1])
            if entry['idc'] == 'IDC2':
                self.voice_ip = ip
                self.voice_port = port
        if voice_data["webrtc"]:
            w = voice_data["webrtc"]
            if w.get('domains'):
                self.sdk_domain = w['domains'][0]
        region_val = raw_p.get('2') or raw_p.get('3')
        if region_val and isinstance(region_val, str) and region_val.isalpha():
            self.region_prefix = region_val.upper()
        else:
            self.region_prefix = "ME"
        self.ext_region = "ME" if self.region_prefix == "ME" else self.region_prefix.lower()[:2]
        ld_proto = decode_login_data(login_data_resp)
        online_port_str = getattr(ld_proto, 'Online_IP_Port', None) or getattr(ld_proto, 'online_ip_port', None)
        account_port_str = getattr(ld_proto, 'AccountIP_Port', None) or getattr(ld_proto, 'account_ip_port', None)
        if online_port_str and ':' in online_port_str:
            parts = online_port_str.split(":")
            self.online_ip = parts[0]
            self.online_port = int(parts[1])
        if account_port_str and ':' in account_port_str:
            parts = account_port_str.split(":")
            self.chat_ip = parts[0]
            self.chat_port = int(parts[1])
        if self.chat_ip and self.chat_port:
            try:
                chat_auth_hex = build_auth_startup(self.uid, self.token, self.timestamp, self.key, self.iv, mode="chat")
                cr, cw = await asyncio.wait_for(asyncio.open_connection(self.chat_ip, self.chat_port), timeout=5.0)
                self.chat_reader = cr
                self.chat_writer = cw
                cw.write(bytes.fromhex(chat_auth_hex))
                await cw.drain()
                asyncio.create_task(self.chat_read_loop(cr))
                asyncio.create_task(self.chat_keepalive_loop(cw))
            except Exception as e:
                log("CHAT", f"Early connect failed: {e}")
        try:
            ok = await equip_emote(self.token, self.login_url)
            log("EVO", f"ChooseEmote => {'OK' if ok else 'FAILED'}")
        except Exception as e:
            log("EVO", f"ChooseEmote error: {e}")
        auth_hex = build_auth_startup(self.uid, self.token, self.timestamp, self.key, self.iv, mode="online")
        reader, writer = await connect_online(self.online_ip, self.online_port, auth_hex)
        if not writer:
            return
        self.writer = writer
        asyncio.create_task(ping_loop(writer, build_ping_packet, self.key, self.iv))
        await read_loop(reader, self.handle_tcp_data, self.key, self.iv)


async def main():
    config_path = "config.json"
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            json.dump({"telegram_token": "YOUR_TOKEN_HERE"}, f, indent=4)
    accounts = load_accounts("accs.json")
    if not accounts:
        log("SYSTEM", "No accounts in accs.json")
        return
    active_bots = []
    for uid, pwd in accounts:
        bot = Bot(uid, pwd)
        active_bots.append(bot)
    tasks = [bot.run() for bot in active_bots]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("SYSTEM", "Exiting...")