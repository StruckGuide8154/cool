from pathlib import Path

def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"Expected source text not found in {path}")
    p.write_text(s.replace(old, new, 1))

# Security-key-only behavior.
replace_once(
    "application.fam",
    'dev_fido2_1 = env_flag("ZEROFIDO_DEV_FIDO2_1", False)\npacked_attestation = env_flag("ZEROFIDO_PACKED_ATTESTATION", True)',
    'dev_fido2_1 = env_flag("ZEROFIDO_DEV_FIDO2_1", False)\nsecurity_key_only = env_flag("ZEROFIDO_SECURITY_KEY_ONLY", False)\npacked_attestation = env_flag("ZEROFIDO_PACKED_ATTESTATION", True)',
)
replace_once(
    "application.fam",
    '    f"ZF_DEV_FIDO2_1={1 if dev_fido2_1 else 0}",\n    f"ZF_PACKED_ATTESTATION={1 if packed_attestation else 0}",',
    '    f"ZF_DEV_FIDO2_1={1 if dev_fido2_1 else 0}",\n    f"ZF_SECURITY_KEY_ONLY={1 if security_key_only else 0}",\n    f"ZF_PACKED_ATTESTATION={1 if packed_attestation else 0}",',
)
replace_once(
    "src/ctap/response.c",
    '        zf_cbor_encode_text(&enc, "rk") && zf_cbor_encode_bool(&enc, true) &&',
    '''#if defined(ZF_SECURITY_KEY_ONLY) && ZF_SECURITY_KEY_ONLY
        zf_cbor_encode_text(&enc, "rk") && zf_cbor_encode_bool(&enc, false) &&
#else
        zf_cbor_encode_text(&enc, "rk") && zf_cbor_encode_bool(&enc, true) &&
#endif''',
)
replace_once(
    "src/ctap/commands/make_credential.c",
    '    resident_key = scratch->request.has_rk && scratch->request.rk;',
    '''    resident_key = scratch->request.has_rk && scratch->request.rk;
#if defined(ZF_SECURITY_KEY_ONLY) && ZF_SECURITY_KEY_ONLY
    if (resident_key) {
        status = ZF_CTAP_ERR_UNSUPPORTED_OPTION;
        goto cleanup;
    }
#endif''',
)

# iPhone two-touch NFC flow:
# after RF field loss, re-enable RX for a fresh activation instead of leaving
# the NFC listener in low-power idle.
replace_once(
    "src/transport/nfc_engine.c",
    '''        case Iso14443_3aListenerEventTypeFieldOff:
            zf_transport_nfc_trace_event("iso3-field-off");
            zf_transport_nfc_on_disconnect(app);
            return NfcCommandSleep;''',
    '''        case Iso14443_3aListenerEventTypeFieldOff:
            zf_transport_nfc_trace_event("iso3-field-off");
            zf_transport_nfc_on_disconnect(app);
            return NfcCommandReset;''',
)

print("ZeroFIDO security-key v2 edits applied")
