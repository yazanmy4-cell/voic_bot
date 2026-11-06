import asyncio
from utils import log


async def connect_online(ip, port, auth_hex):
    try:
        reader, writer = await asyncio.open_connection(ip, port)
        writer.write(bytes.fromhex(auth_hex))
        await writer.drain()
        log("NETWORK", f"Online Connection Established ({ip}:{port})")
        return reader, writer
    except Exception as e:
        log("NETWORK", f"Connection Error: {e}")
        return None, None


async def ping_loop(writer, build_ping_packet, key, iv, interval=5.0):
    _PING = bytes.fromhex('0201')
    try:
        while writer and not writer.transport.is_closing():
            try:
                writer.write(_PING)
                await writer.drain()
            except Exception:
                pass
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass


async def read_loop(reader, callback, key, iv):
    log("NETWORK", "Reader Loop Started.")
    try:
        while True:
            data = await reader.read(16384)
            if not data:
                log("NETWORK", "Connection Closed by server.")
                break
            await callback(data)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log("NETWORK", f"Reader Loop Exception: {e}")
    finally:
        log("NETWORK", "Reader Loop Stopped.")