from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


def enc_aes(hex_data):
    key = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    iv = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(bytes.fromhex(hex_data), 16)).hex()


def dec_aes(hex_data):
    key = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    iv = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    return unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(bytes.fromhex(hex_data)), 16).hex()


def enc_packet(hex_data, key, iv):
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(bytes.fromhex(hex_data), 16)).hex()


def dec_packet(hex_data, key, iv):
    return unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(bytes.fromhex(hex_data)), 16).hex()