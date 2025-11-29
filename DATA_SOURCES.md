# Data Sources and Statistics

## Current Status: ⚠️ USING DEFAULT VALUES

**The AI is currently using hardcoded default statistics**, not real team data. This means:

- ❌ **NOT fetching** team form (last 5 matches)
- ❌ **NOT fetching** head-to-head records
- ❌ **NOT fetching** real xG (expected goals) data
- ❌ **NOT fetching** team position in league table
- ❌ **NOT fetching** player injuries/suspensions

### What IS being used:
- ✅ Match fixtures (teams, date, league) - **REAL DATA from Broadage API**
- ✅ Match odds (home/draw/away) - **REAL DATA from Broadage API** (if provided)
- ❌ All statistics (xG, form, position) - **HARDCODED DEFAULTS**

### Default Values Being Used:
```python
'home_xg': 1.8,  # Hardcoded - same for all teams
'away_xg': 1.5,  # Hardcoded - same for all teams
'home_form': {
    'goals_scored_5': 10,  # Hardcoded
    'goals_conceded_5': 4,  # Hardcoded
    'form_percentage': 0.7,  # Hardcoded
    'shots_on_target_avg': 5.0,  # Hardcoded
    'goals_variance': 5.0  # Hardcoded
},
'away_form': { ... },  # Similar hardcoded values
```

## Why This Happened:
1. **Broadage API** (current provider) may not provide detailed team statistics in the basic match list endpoint
2. **API-Football** (alternative) has detailed stats but requires paid plan for current season data
3. The code was written with placeholders for "future implementation"

## Impact:
- The AI can still make safe picks (like `over_0.5_goals`) because these are statistically very safe regardless of team
- However, it cannot differentiate between teams or make data-driven decisions
- It got lucky with the Braunschweig pick, but this is not sustainable

## Solutions:

### Option 1: Use API-Football for Statistics (Recommended)
- API-Football has endpoints for:
  - Team statistics (`/teams/statistics`)
  - Head-to-head (`/fixtures/headtohead`)
  - Team form (`/fixtures` with team filter)
  - League standings (`/standings`)
- Requires paid API-Football plan for current season

### Option 2: Check Broadage API Documentation
- Broadage may have team statistics endpoints we haven't discovered
- Check their documentation for:
  - Team stats endpoints
  - Form/performance endpoints
  - Historical match data

### Option 3: Hybrid Approach
- Use Broadage for match fixtures (free/cheaper)
- Use API-Football for detailed statistics (paid)
- Combine data sources

### Option 4: Conservative Defaults with Transparency
- Keep using defaults but:
  - Clearly mark in reasoning: "Using conservative default statistics"
  - Only recommend ultra-safe markets (over_0.5_goals) that don't require team-specific data
  - Wait until real stats are available before expanding

## Next Steps:
1. ✅ Acknowledge the limitation
2. 🔄 Check Broadage API docs for stats endpoints
3. 🔄 Implement API-Football stats fetching (if paid plan available)
4. 🔄 Update reasoning to indicate when defaults are used

