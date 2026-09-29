from pathlib import Path

p = Path("src/transport/nfc_engine.c")
s = p.read_text()

old = '''        case Iso14443_3aListenerEventTypeFieldOff:
            zf_transport_nfc_trace_event("iso3-field-off");
            zf_transport_nfc_on_disconnect(app);
            return NfcCommandSleep;'''

new = '''        case Iso14443_3aListenerEventTypeFieldOff:
            zf_transport_nfc_trace_event("iso3-field-off");
            zf_transport_nfc_on_disconnect(app);
            return NfcCommandReset;'''

if old not in s:
    raise SystemExit("Expected NFC field-off source not found")

p.write_text(s.replace(old, new, 1))
print("Applied iOS NFC reactivation patch")
