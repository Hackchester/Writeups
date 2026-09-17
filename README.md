<div align="center">

<img src=".repo_images/logo.webp" width="100">

# Hackchester Writeups

</div>


Welcome to the **Hackchester Writeups** repo! This is the central hub where our society members share their knowledge, document their CTF solves, and publish writeups. 

Whenever a Pull Request is merged here, it automatically triggers a build and publishes the latest changes to our official [Hackchester website](https://hackchester.net). 🚀


---

## 📜 Submission Rules & Guidelines

To keep our website looking clean and ensure the automated build process doesn't break, all members **must** adhere to the following rules when submitting a writeup.


### 1. 📂 Directory Structure

Keep your writeups organized. Place your submission in the appropriate year and competition folder. If the folders don't exist, create them!

```text
📁 writeups/
 ┣ 📂 2026/
 ┃ ┣ 📂 picoCTF/
 ┃ ┃ ┗ 📜 cookies-2.md
 ┃ ┣ 📂 hackthebox/
 ┃ ┗ 📂 tryhackme/
 ┗ 📂 assets/
   ┗ 📂 2026/
     ┗ 🖼️ cookies-webapp-screenshot.png
```
### 2. 📝 Required Markdown Format (Frontmatter)
Since this repo feeds into our website, **every writeup must start with YAML frontmatter**. This tells the website's engine how to display your post. 

Copy and paste this at the very top of your `.md` file:

```yaml
---
title: "Challenge Name"
author: "Your Name"
date: YYYY-MM-DD
categories: ["Web", "CTF Name"]
tags: ["sqli", "rce"]
partial_solve: false
used_ai: true
---
```

### 3. 🖼️ Image Handling
Images are great, but heavy images slow down our site.
- Store all images in the root `/assets/YYYY/` folder.
- **Compress your images** before uploading. (Use tinypng.com or similar).
- Reference images in your markdown like this: `![Alt Text](../../assets/2026/your-image.png)`

### 4. 🚀 How to Submit (The Workflow)
1. **Fork** this repository.
2. **Clone** your fork locally: `git clone https://github.com/your-username/writeups.git`
3. **Create a branch**: `git checkout -b writeup/your-username/challenge-name`
4. **Write** your awesome writeup!
5. **Commit & Push**: `git commit -m "Add writeup for [Challenge Name]"` -> `git push origin your-branch-name`
6. Open a **Pull Request** back to the `main` branch of this repository.

---

## ❓ Frequently Asked Questions (FAQ)

<details>
  <summary><strong>Can I submit a writeup for an older competition?</strong></summary>
  <br>
  Absolutely. Just ensure you place your submission in the folder corresponding to the year the competition took place (e.g., /2025/picoCTF/ ), even if you are submitting it today.
</details>
<details>
  <summary><strong>Can I publish a writeup for a competition that is still active?</strong></summary>
  <br>
  No. Please wait until the competition officially ends and the organizers permit writeup publications before opening your Pull Request.
</details>
<details>
  <summary><strong>Should I include the actual flag in my writeup?</strong></summary>
  <br>
  It is best practice to redact the final flag (e.g., <code>flag{REDACTED}</code> or <code>HTB{...}</code>) so readers can still follow your guide and get the satisfaction of submitting the real flag themselves.
</details>
<details>
  <summary><strong>What if I only got the user flag, but not root?</strong></summary>
  <br>
  Partial solves are totally fine! Documenting your thought process, your initial foothold, and how far you got is still really valuable. Just make it clear in your introduction where the writeup ends, and be sure to add <code>partial_solve: true</code> to your YAML frontmatter.
</details>
<details>
  <summary><strong>Why isn't my writeup showing up on the website?</strong></summary>
  <br>
  If your PR was merged but the site hasn't updated, the build likely failed. Double-check your YAML frontmatter for formatting errors and verify your image paths are perfectly matched. If you're still stuck, ping a committee member in the Discord.
</details>
<details>
  <summary><strong>Can I use AI to make the writeup?</strong></summary>
  <br>
  Yes, you can! However, you must explicitly state this by adding <code>used_ai: true</code> to the YAML frontmatter at the top of your submission.
</details>

## 🤝 Need Help?
Stuck on formatting or git? Drop a message in the Hackchester [Discord server](https://discord.gg/pPenRa2ewq) in the `#ctf-help` channel, and a committee member will help you out!

<div align="center">
  <i>Happy Hacking! 💻✨</i>
</div>

