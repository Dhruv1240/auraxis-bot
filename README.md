🌟 Auraxis - AI-Powered Aura Tracking Bot

Auraxis is a next-generation Discord bot that measures the "aura" of users based on message sentiment, positivity, and community impact. Built with AI-driven toxicity detection, multi-language support (English, Hindi, Hinglish), and deep analytics.





🚀 Features
✨ Smart Aura System

* AI-powered sentiment analysis using sentence-transformers and transformers
* Multilingual support: English, Hindi, and Hinglish culture-aware detection
* Real-time toxicity classification with hate speech protection

⚔️ Battles & Competitions

* Challenge others to aura duels with dynamic win chances
* Weekly tournaments with global rankings
* Battle shields, streaks, and random events (critical hits, dodges!)

🛒 Customization & Shop

* Buy titles, badges, colors, and boosts
* Equip cosmetics on your aura card
* 2x aura boost & battle shield items

📊 Analytics & Insights

* Global and server leaderboards
* Aura prediction and trend analysis
* Detailed stats, logs, and historical graphs
* Server comparison & health metrics

🎨 Stunning Visuals

* Generate beautiful aura cards with dynamic themes
* Progress bars, win rates, and interactive buttons
* Text fallback for servers without Pillow


🛠️ Setup Guide
1. Prerequisites

* Python 3.9+
* Discord Bot Token
* OpenRouter API Key (for AI moderation)

2. Install Dependencies
bashDownloadCopy codepip install discord.py sentence-transformers transformers torch pillow aiohttp openai
3. Environment Variables
Create a .env file:
envDownloadCopy codeTOKEN=your_discord_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
4. Run the Bot
bashDownloadCopy codepython bot.py

📋 Commands
🌟 Core
CommandDescription/auraCheck your aura score/auracardView your profile card/aurastatsDetailed aura analytics/aurapredictPredict future aura based on trends
⚔️ Battles
CommandDescription/aurabattle @userChallenge someone to a duel/battlestatsView win/loss record
📅 Daily & Streaks
CommandDescription/dailyClaim daily aura reward/streakCheck your daily streak
🛍️ Shop & Cosmetics
CommandDescription/shopBrowse titles, badges, boosts/buy item_idPurchase an item/equip item_idEquip cosmetics/inventoryView your collection
🏆 Competitions
CommandDescription/tournamentView weekly tournament/globalboardGlobal leaderboard/servercompareCompare servers
⚙️ Admin
CommandDescription/aurach_enableEnable aura in channel/aurach_disableDisable aura in channel/setaura @user 1000Set user's aura/resetuser @userReset user's aura/serverauraServer-wide analytics

🧠 How Aura Works
✅ Gain Aura By:

* Positive, helpful messages (+1 to +5)
* Daily check-ins (10–60 aura)
* Winning battles (5–100 aura)
* Long messages with engagement
* Friendly banter (Hinglish-friendly!)

❌ Lose Aura For:

* Toxic or targeted messages (-1 to -3)
* Hate speech or extremism (-5)
* Losing battles
* Weekly decay (2% if inactive)


Note: Casual Hinglish swears like "bc mast hai" are not penalized in friendly contexts!


🌍 Global Leaderboard
Auraxis syncs across servers to create a global leaderboard. Your position updates automatically based on your current aura.
Use /globalboard to see top players across all communities.

🛡️ Safety & Moderation

* 🔒 Hate Speech Detection – Blocks racism, extremism, and discrimination
* 🧠 AI-Powered Moderation – Uses devstral-2512 for cultural context
* 🛑 Message Deletion – Auto-deletes severe violations
* 📉 Decay System – Inactive users slowly lose aura (2% weekly)


🖼️ Aura Card Example

Sample aura card with dynamic theme, battle stats, and active boosts

🤝 Contributing
Contributions are welcome! Feel free to:

* Report bugs
* Suggest new features
* Improve AI detection
* Add new languages

Fork the repo and open a PR!

📄 License
MIT © 2026 Auraxis Team

📞 Support
Have questions? Join our Discord Support Server or open an issue.


Auraxis — Where every message shapes your energy. ⚡
Stay positive. Gain aura. Rise the ranks. 🌟