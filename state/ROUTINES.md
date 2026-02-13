# ROUTINES - Daily Checkpoints

## 🌅 Morning Routine (6:00 AM PT)

1. **Read state/current.md** - Know exactly where we stand
2. **Run premarket scanner** - Find new setups
3. **Check overnight positions** - Any gaps/news?
4. **Review stop-losses** - Any triggers hit?
5. **Send morning briefing** - Summary to Telegram
6. **Update state/current.md** - Today's focus

## 🕐 Checkpoint (Every 30min during market hours)

1. **Quick portfolio check** - Any alerts needed?
2. **Update state/current.md** - Position changes
3. **Check for stop triggers** - Down >12%?
4. **Monitor profit targets** - Up >30%?

## 🌆 Market Close (1:00 PM PT / 4:00 PM ET)

1. **Run daily_portfolio_review.py** - MANDATORY
2. **Run scanner** - After-hours setups
3. **Send daily summary** - P&L, trades, learnings
4. **Update state/current.md** - Complete EOD state
5. **Log to memory/YYYY-MM-DD.md** - Daily record
6. **Update MEMORY.md** - Key learnings

## 📊 Friday Evening (6:00 PM PT) - WEEKLY REVIEW

1. **Run performance_projections.py** - MANDATORY
2. **Send weekly performance report** - Annual projections to Telegram
3. **Run scanner learning analysis** - Review week's picks
4. **Update MEMORY.md** - Weekly lessons learned
5. **Plan next week** - Strategy adjustments

## 📈 First Trading Day of Month - MONTHLY REVIEW

1. **Run performance_projections.py** - MANDATORY
2. **Send monthly performance report** - Full projections to Telegram
3. **Compare to last month** - Track improvement trend
4. **Review all closed trades** - Win rate, avg gains
5. **Adjust strategy if needed** - Based on monthly data

## 🌙 Evening Routine (8:00 PM PT)

1. **Final scan** - After-hours opportunities
2. **Review day's trades** - What worked/didn't?
3. **Prepare tomorrow's watchlist** - Top setups
4. **Update state/nightly-backlog.md** - Tasks for tomorrow
5. **Commit all changes** - Git push

---

## 🚨 Emergency Checks (Anytime)

**Trigger: Position down >10%**
- Check stop-loss status
- Alert immediately
- Consider exit

**Trigger: Position up >30%**
- Scale out 50%
- Trail remaining shares
- Lock in profits

**Trigger: Daily spend approaching $300**
- STOP all new trades
- Alert before limit hit

---

_Follow these routines religiously. No exceptions._
