---
title: "SiteCheck"
author: "arkb"
date: 2026-09-26
categories: ["Web", "SunshineCTF"]
tags: ["SSRF", "Ping"]
partial_solve: false
used_ai: false
---

## Challenge
> Welcome to **SiteCheck**, the SkyCity fleet's favorite web-diagnostics service since 2062!

> Enlist for a free inspector account and put any website through its paces: our autonomous inspection drone flies out to the address you provide, clocks how long the page takes to load, tallies how many files it pulls down, and beams back a crisp viewport snapshot — all without you lifting a finger.

> Kick the tires on the future of web monitoring.


## Recon
![sitecheck1](../../assets/2026/sitecheck/sitecheck1.png)
After registering and logging in, we were presented with a URL inspection feature. The server visits the supplied URL, measures page load statistics, and returns a screenshot of the rendered page.

I first tested the functionality with `https://google.com`, which returned a screenshot of Google's homepage.

![sitecheck2](../../assets/2026/sitecheck/sitecheck2.png)


## Exploit
Since the application fetches arbitrary URLs, I tested for SSRF. Common localhost representations were blocked by the server-side validation:

- `http://127.0.0.1:3000`
- `http://0.0.0.0:3000`
- `http://2130706433:3000`
- `http://0x7f000001:3000`
- `http://0177.0.0.1:3000`

![sitecheck3](../../assets/2026/sitecheck/sitecheck3.png)

However, the IPv6 loopback address bypassed the filter:
`http://[::1]:3000`

![sitecheck7](../../assets/2026/sitecheck/sitecheck7.png)


From the navigation bar, I knew that the 'Personnel file' was in the `/profile` route.

So I submitted `http://[::1]:3000/profile`, and the server returned:

![sitecheck6](../../assets/2026/sitecheck/sitecheck6.png)

The goal now was to make the server scroll down before taking the screenshot. 
I visited the `/profile` from my browser and saw that there was part of the page with id=clearance, and it displayed the following:

![sitecheck5](../../assets/2026/sitecheck/sitecheck5.png)

So I submitted `http://[::1]:3000/profile` again but this time as ``http://[::1]:3000/profile#clearance`, and the server responded with the flag:

![sitecheck4](../../assets/2026/sitecheck/sitecheck4.png)