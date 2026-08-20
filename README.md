# ClankerWrangler

ClankerWrangler is a tiny home base for shared coding-agent rules and skills.

## Why ClankerWrangler?

I was getting tired of configuring all my different coding agents across my machines, so I decided to centralize them into one repo with a handy script. One set of rules, one skills folder, fewer tiny setup chores nibbling at my day.

## How To Run

Open an Administrator PowerShell window from this repo and run:

```powershell
.\wrangle.ps1
```

The script wires the shared rules and skills into the supported agent config locations.

## Legacy Skills

Deprecated skills live in `skills/legacy/`. They are not installed, and `wrangle.ps1` deletes any previously installed copy of them from each agent's skills folder on the next run.

## Step 4

💰 PROFIT. 💰
