from pathlib import Path

# Fresh AAGUID only. Do not alter CTAP credential semantics.
p = Path("src/zerofido_attestation.c")
s = p.read_text()

old_bytes = """static const uint8_t zf_attestation_aaguid[ZF_AAGUID_LEN] = {
    0xb5, 0x1a, 0x97, 0x6a, 0x0b, 0x02, 0x40, 0xaa, 0x9d, 0x8a, 0x36, 0xc8, 0xb9, 0x1b, 0xbd, 0x1a,
};"""
new_bytes = """static const uint8_t zf_attestation_aaguid[ZF_AAGUID_LEN] = {
    0x2a, 0x77, 0x91, 0x5e, 0x54, 0x3f, 0x4d, 0xc2, 0xa1, 0x6b, 0x85, 0x32, 0xd4, 0x7f, 0x20, 0x6c,
};"""
old_str = 'static const char zf_attestation_aaguid_string[] = "b51a976a-0b02-40aa-9d8a-36c8b91bbd1a";'
new_str = 'static const char zf_attestation_aaguid_string[] = "2a77915e-543f-4dc2-a16b-8532d47f206c";'

if old_bytes not in s or old_str not in s:
    raise SystemExit("Expected upstream AAGUID not found")

s = s.replace(old_bytes, new_bytes, 1).replace(old_str, new_str, 1)
p.write_text(s)

# Fresh storage namespace so registration starts clean, but preserve original store logic.
p = Path("src/zerofido_types.h")
s = p.read_text()
old = '#define ZF_APP_DATA_DIR ZF_APP_DATA_ROOT "/" ZF_APP_ID'
new = '#define ZF_APP_DATA_DIR ZF_APP_DATA_ROOT "/zf2a77915e"'
if old not in s:
    raise SystemExit("Expected upstream storage path not found")
p.write_text(s.replace(old, new, 1))

print("Applied fresh identity only; CTAP/store behavior unchanged")
