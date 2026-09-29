from pathlib import Path

# Fresh identity and isolated storage namespace.
p = Path("src/zerofido_attestation.c")
s = p.read_text()

old_bytes = """static const uint8_t zf_attestation_aaguid[ZF_AAGUID_LEN] = {
    0xb5, 0x1a, 0x97, 0x6a, 0x0b, 0x02, 0x40, 0xaa, 0x9d, 0x8a, 0x36, 0xc8, 0xb9, 0x1b, 0xbd, 0x1a,
};"""
new_bytes = """static const uint8_t zf_attestation_aaguid[ZF_AAGUID_LEN] = {
    0x6d, 0x51, 0x7a, 0x29, 0x6e, 0x9b, 0x4a, 0x71, 0x93, 0xd2, 0x44, 0x5a, 0x8d, 0xb3, 0x26, 0xf1,
};"""
old_str = 'static const char zf_attestation_aaguid_string[] = "b51a976a-0b02-40aa-9d8a-36c8b91bbd1a";'
new_str = 'static const char zf_attestation_aaguid_string[] = "6d517a29-6e9b-4a71-93d2-445a8db326f1";'

if old_bytes not in s or old_str not in s:
    raise SystemExit("Expected upstream AAGUID source not found")
s = s.replace(old_bytes, new_bytes, 1).replace(old_str, new_str, 1)
p.write_text(s)

p = Path("src/zerofido_types.h")
s = p.read_text()
old = '#define ZF_APP_DATA_DIR ZF_APP_DATA_ROOT "/" ZF_APP_ID'
new = '#define ZF_APP_DATA_DIR ZF_APP_DATA_ROOT "/zerofido_usb_classic_6d517a29"'
if old not in s:
    raise SystemExit("Expected app data dir source not found")
p.write_text(s.replace(old, new, 1))

# Advertise rk=false in authenticatorGetInfo.
p = Path("src/ctap/response.c")
s = p.read_text()
old = '''             zf_cbor_encode_text(&enc, "rk") && zf_cbor_encode_bool(&enc, true) &&'''
new = '''             zf_cbor_encode_text(&enc, "rk") && zf_cbor_encode_bool(&enc, false) &&'''
if old not in s:
    raise SystemExit("Expected rk option source not found")
p.write_text(s.replace(old, new, 1))

# Reject resident/discoverable credential requests.
p = Path("src/ctap/commands/make_credential.c")
s = p.read_text()
needle = "    resident_key = scratch->request.has_rk && scratch->request.rk;\n"
insert = """    resident_key = scratch->request.has_rk && scratch->request.rk;
    if (resident_key) {
        status = ZF_CTAP_ERR_UNSUPPORTED_OPTION;
        goto cleanup;
    }
"""
if needle not in s:
    raise SystemExit("Expected resident-key source not found")
p.write_text(s.replace(needle, insert, 1))

print("Applied classic USB roaming security-key profile")
