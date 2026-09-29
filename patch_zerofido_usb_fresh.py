from pathlib import Path

p = Path("src/zerofido_attestation.c")
s = p.read_text()

old_bytes = """static const uint8_t zf_attestation_aaguid[ZF_AAGUID_LEN] = {
    0xb5, 0x1a, 0x97, 0x6a, 0x0b, 0x02, 0x40, 0xaa, 0x9d, 0x8a, 0x36, 0xc8, 0xb9, 0x1b, 0xbd, 0x1a,
};"""
new_bytes = """static const uint8_t zf_attestation_aaguid[ZF_AAGUID_LEN] = {
    0x9b, 0x23, 0x46, 0x33, 0x64, 0x94, 0x4a, 0x42, 0x91, 0x34, 0xed, 0x9e, 0x08, 0x62, 0x9b, 0xdd,
};"""
old_str = 'static const char zf_attestation_aaguid_string[] = "b51a976a-0b02-40aa-9d8a-36c8b91bbd1a";'
new_str = 'static const char zf_attestation_aaguid_string[] = "9b234633-6494-4a42-9134-ed9e08629bdd";'

if old_bytes not in s or old_str not in s:
    raise SystemExit("Expected upstream AAGUID source not found")

s = s.replace(old_bytes, new_bytes, 1).replace(old_str, new_str, 1)
p.write_text(s)

p = Path("src/zerofido_types.h")
s = p.read_text()
old = '#define ZF_APP_DATA_DIR ZF_APP_DATA_ROOT "/" ZF_APP_ID'
new = '#define ZF_APP_DATA_DIR ZF_APP_DATA_ROOT "/zerofido_usb_fresh_9b234633"'
if old not in s:
    raise SystemExit("Expected app data dir source not found")
p.write_text(s.replace(old, new, 1))

print("Applied fresh USB authenticator identity")
