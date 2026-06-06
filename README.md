# Nazik Connect Bot 🤖

Telegram bot for the **Nazik Connect** trading community (MetaTrader 5).  
Languages: **Türkmençe + Русский**

---

## Features

- ✅ Auto-welcome new group members (short message in group, full flow in DM)
- ✅ Bonus selection flow (250$ / 500$ / 1000$)
- ✅ PU Prime affiliate link integration
- ✅ Video guidance for account opening & deposit
- ✅ VIP Signals group invite after deposit
- ✅ Admin notifications for every action
- ✅ `/stats` command for admin
- ✅ Link filter in group (auto-delete unauthorized links)

---

## Environment Variables

Set these in Railway:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | Your bot token from @BotFather |
| `ADMIN_USERNAME` | `verifyhof` |
| `ADMIN_CHAT_ID_1` | `8474703406` |
| `ADMIN_CHAT_ID_2` | `8808544262` |
| `SIGNAL_GROUP_LINK` | `https://t.me/+s0ACkwJ143E5Y2Y0` |
| `VIDEO_1_LINK` | YouTube link for account opening video |
| `VIDEO_2_LINK` | YouTube link for bonus/deposit video |

---

## Deploy on Railway

1. Push this repo to GitHub
2. Create new Railway project → Deploy from GitHub
3. Set environment variables above
4. Railway will auto-deploy the worker

---

## Bot Info

- **Bot username:** @nazikconnect_bot
- **Main group:** MetaTrader 5 — https://t.me/+wZdBwJCpYpAwMTQ0
- **VIP Signals:** https://t.me/+s0ACkwJ143E5Y2Y0
- **Broker:** PU Prime — https://puvip.co/la-partners/777999

---

## Admin Commands

| Command | Description |
|---|---|
| `/start` | Start the bot (DM) |
| `/stats` | Show statistics (admin only) |
| `/davet` | Show group invite link |
