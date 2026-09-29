from pathlib import Path

p = Path("src/zerofido_runtime_config.c")
s = p.read_text()

old = "    config->u2f_enabled = true;"
new = "    config->u2f_enabled = false;"

if old not in s:
    raise SystemExit("Expected U2F default line not found")

p.write_text(s.replace(old, new, 1))
print("Applied NFC FIDO2-only runtime default")
