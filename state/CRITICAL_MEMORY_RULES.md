# CRITICAL MEMORY RULES

## The Problem
You keep forgetting things that happened earlier in the day because you don't check your memory files before responding.

## The Solution

**BEFORE answering ANY question about:**
- Portfolio status
- What trades happened
- Current positions
- "Did you do X?"
- Account status

**YOU MUST:**
1. Read `state/current.md` FIRST
2. Read today's `memory/YYYY-MM-DD.md` SECOND
3. THEN answer based on what you READ, not what you think

## Example of WRONG behavior:
```
User: "I thought you already sold those profits"
Agent: "Let me check portfolio..." (checking API instead of memory)
```

## Example of RIGHT behavior:
```
User: "I thought you already sold those profits"
Agent: [Reads state/current.md] "You're right! I sold 50% PTNM and SSRM at 9:12 AM this morning. Here's what's left..."
```

## The Rule
**TEXT FILES > YOUR MEMORY**

If it's written down, that's the truth. Check files first, ALWAYS.

## Files to check (in order):
1. `state/current.md` - Current state of everything
2. `memory/YYYY-MM-DD.md` (today) - What happened today
3. `memory/YYYY-MM-DD.md` (yesterday) - Recent context

## When to update files:
- After EVERY trade
- After EVERY important action
- After EVERY decision

## The commitment:
From now on, when Mike asks "did you do X?", the FIRST thing you do is read the relevant memory file. No exceptions.
