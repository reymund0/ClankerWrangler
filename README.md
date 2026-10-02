# ClankerWrangler

ClankerWrangler is a tiny home base for shared coding-agent rules and skills.

## Why ClankerWrangler?

I was getting tired of configuring all my different coding agents across my machines, so I decided to centralize them into one repo with a handy script. One set of rules, one skills folder, fewer tiny setup chores nibbling at my day.

## How To Run

**Windows** — Open an Administrator PowerShell window from this repo and run:

```powershell
.\wrangle.ps1
```

**Mac / Unix** — Open a terminal from this repo and run:

```bash
./wrangle.sh
```

The script wires the shared rules and skills into the supported agent config locations.

## Routing Editor

From the repo root, run `npm run dev` and open the printed local URL.

First time? You'll need Python 3.10+ and Node 20.19+ (or 22.12+), then:

```bash
npm --prefix routing-editor ci
npm run build
npm run dev
```

## Step 4

💰 PROFIT. 💰
