# F1 2024 Voice Engineering Reference

**Live Race Strategy Framework for Voice AI Assistant**

This document provides specific, actionable thresholds and decision frameworks that inform voice responses. Use these to build system prompts and response templates for real-time race engineering advice.

---

## 1. TYRE MANAGEMENT FRAMEWORK

### Compound Performance Deltas
```
Soft vs Medium:    0.4–1.2 sec/lap faster (circuit-dependent)
Soft vs Hard:      1.2–1.8 sec/lap faster
Medium vs Hard:    0.4–0.8 sec/lap
```

### Pit Stop Triggers (When to Tell Driver to Box)

**Tyre Wear Degradation**
- Softer compounds wear faster; harder compounds preserve grip longer
- **Pit trigger threshold**: Tyre wear ≥ 70% (performance degradation becomes severe)
- Monitor via telemetry: `m_driver_data[driver_id].m_tyres.m_wear[tyre_index]`

**Tyre Saving Techniques** (Engineer callouts)
- *"Manage the rear; ease off braking aggression"* → Reduces rear heat load
- *"Shift brake bias rearward by 1–2%"* → Reduces front wear, slight pace loss
- *"Enter fuel saving mode"* → 0.1–0.2 sec/lap cost; ~3% fuel consumption reduction
- *"Late-race fuel saving modes reduce temps but cost 0.1–0.2 sec/lap"*

### Radio Script Templates

```
Tyre alert (wear > 65%):
  "Tyre window opening. Prepare to box lap [window_start]–[window_end]."

Tyre saving mode:
  "Manage the rear; we need to extend this stint 4 more laps."

Compound strategy:
  "Soft to medium pit stop. Will cost us 0.6 sec/lap initially but tyres stable lap 8+ of stint."
```

---

## 2. FUEL STRATEGY & CALCULATIONS

### Tank & Burn Rates

```
Max capacity:           110 kg per race
Typical consumption:    ~1.7 kg/lap
Burn rate limit:        100 kg/hour (FIA rule)
```

### Fuel Mix Impact on Consumption & Pace

| Fuel Mix Mode | Pace Impact | Consumption Impact | Use Case |
|---------------|-------------|-------------------|----------|
| **Standard** | Baseline (0 sec/lap) | 1.7 kg/lap baseline | Early race; building gap |
| **P2 (Lean)** | −0.1 sec/lap | 3% reduction (~1.65 kg/lap) | 5–8 sec gap to threat |
| **P3 (Leaner)** | −0.15 sec/lap | 5% reduction (~1.6 kg/lap) | 8+ sec gap; final stint |
| **P4 (Leanest)** | −0.2 sec/lap | 8% reduction (~1.56 kg/lap) | Final 10 laps; gap secure |

### Fuel Pit Window Calculation

**When pit window opens:**
- Calculate: `remaining_fuel / (burn_rate_in_saving_mode) = laps_remaining`
- If `laps_remaining ≤ 2`, pit window OPEN (must stop next 1–3 laps)
- If `laps_remaining > 3`, window closed (can extend 2–3 more laps)

**Example calculation:**
```
Current fuel:       25 kg
Burn rate (lean):   1.65 kg/lap
Remaining laps:     25 kg / 1.65 = 15.15 laps
Gap to P2:          3 seconds
Decision:           If ≤ 2 laps before stop needed, pit this lap (undercut opportunity)
                    If 3+ laps, stretch 1–2 more laps (build gap before pit)
```

### Radio Script Templates

```
Fuel strategy (building gap):
  "Ideal mix until pit stop. Let's extend to lap [target_pit_lap]. Build 2–3 second gap."

Fuel strategy (gap secure):
  "Switch to P2 fuel mix lap [current_lap]. You're [gap] sec clear. We'll box lap [pit_lap]."

Fuel critical (final stint):
  "15 laps remaining. Lock to P3 lean fuel; manage pace. Accept 0.15 sec/lap cost."

Undercut pit decision:
  "P2 is 1.8 seconds behind. Box this lap—new tyres will undercut by 2.5+ seconds."
```

---

## 3. PACE ANALYSIS & GAP MANAGEMENT

### When to Push vs. Manage (Decision Table)

| Gap to Threat | Situation | Action | Fuel Mix | Brake Bias |
|---------------|-----------|--------|----------|-----------|
| **0.1–0.5 sec** | DRS range; critical position | Manage; defend | P2 lean | Rear +1% |
| **0.5–1.5 sec** | Vulnerable undercut window | Extend 2–3 laps; build gap | Standard | Neutral |
| **1.5–3 sec** | Safe from undercut; pit threats exist | Standard pace until pit | Standard | Neutral |
| **3–5 sec** | Moderate gap; can fuel-save | Fuel-save mode; manage tyres | P2 | Neutral |
| **5+ sec** | Safe gap; no immediate threat | Full fuel-save; conservative tyres | P3–P4 | Rear +2% |

### Lap Time Deltas for Pit Strategy

```
Gap < 0.3 sec:  CRITICAL — Prepare immediate pit or aggressive defense
Gap 0.3–0.5 sec: Marginal undercut window — Pit next 1–2 laps if tyres worn
Gap 0.5–1.0 sec: Safe to switch fuel saving without losing position
Gap 1.0–2.0 sec: Safe from undercut; can manage tyres aggressively
Gap > 2.0 sec:  Leader can adopt lean fuel; easy margin maintained
Gap > 5.0 sec:  Full conservation mode; retire into saving lap times
```

### Radio Script Templates

```
Leading with margin:
  "Push to extend gap to 3+ seconds, then settle into fuel-saving rhythm."

Under DRS threat (gap < 1.0 sec):
  "Manage tyres. P2 is in DRS window. Prepare turn 1 defense next lap."

Chasing via undercut:
  "Gap is 2.8 seconds. Plan pit lap [target_pit_lap]—new softs should undercut by 2+ sec."

Final stint (gap secure):
  "6-second gap with 12 laps left. Lock to P3 fuel; zero risk. Manage the tyres."
```

---

## 4. PIT WINDOW OPTIMIZATION

### Stop Duration & Performance Cost

```
Total pit stop time:    2.5–3.0 seconds (wheel change + signal + exit)
Pit lane speed limit:   80 km/h (60 km/h on narrow circuits: Monaco, Singapore, Australia, Zandvoort)
Cost of pit stop:       Equivalent to ~2.5 seconds of track time
```

### Undercut vs. Overcut Decision Logic

**Undercut wins when:**
```
new_tyre_lap_time < old_tyre_lap_time + pit_stop_cost_time

Example:
  Old tyre pace:        1m 25s (degraded)
  New tyre pace:        1m 22.5s (fresh soft)
  Pit stop cost:        2.5s
  Lap time delta:       1m 22.5s vs (1m 25s + 2.5s) = 1:25 gain
  Result:               Fresh tyres undercut, gain position
```

**Overcut wins when:**
```
track_position_advantage + remaining_pace > pit_stop_cost

Example:
  Leader on lap 18; trailing P2 by 1.2 sec
  P2 pits lap 18; P1 stays out 2 more laps
  P1 can extend tyres 1.8 sec over 2 laps (gap increases to 3 sec)
  P1 pits lap 20; emerges ahead of P2
  Result:               Overcut gains position via fresh tyres when leader exits
```

### Pit Window Decision Script

```
IF gap_to_threat < 1.5 sec AND tyre_wear > 65%:
  → "Box this lap—undercut threat imminent; fresh tyres will gain 2+ sec"

IF gap_to_threat > 2 sec AND tyre_wear < 60%:
  → "Box in 2 laps. Extend the stint; we're clear of undercut."

IF leader_pits_this_lap AND gap > 2 sec:
  → "Stay out 2 more laps. New tyres when you exit will overcut. Fresh tyres in clear air."

IF fuel_window_opens AND tyre_wear > 70%:
  → "Pit window open. Box lap [X]—tyres critical, fuel near limit."
```

---

## 5. SETUP ADJUSTMENTS (IN-RACE CALLOUTS)

### Brake Balance Adjustments

```
Operating range:       54–58% front bias
Impact per 1–2% change: 0.1–0.3 sec/lap
```

**When to adjust:**
- **Front wear critical (>75%)**: Shift bias **+1–2% rear** → Reduces front load, slight pace loss but extends front tyre life
- **Rear tyre wear critical**: Shift bias **+2–3% front** → Increases rear load, extends rear life
- **Fuel saving mode**: Shift bias **+1% rear** → Reduces braking aggression, lower temperatures

### Wing Angle & Downforce

```
Impact per notch:       0.2–0.5 sec/lap (circuit-specific)
Trade-off:              More downforce = higher corner speed + more drag = lower top speed
```

**Tactical adjustments:**
- **Fuel-saving stint**: Reduce wing by 1–2 notches → Lower drag, reduces fuel consumption
- **Defending undercut**: Increase wing by 1 notch → More corner speed, compensate for fuel load
- **Final stint (light fuel)**: Increase wing by 1 notch → Lighter car, higher downforce stability

### Engine & Fuel Mix Modes (Already covered in Fuel Strategy)

### Radio Script Templates

```
Brake balance (tyre wear management):
  "Front tyres wearing faster than rear. Shift brake bias +1.5% rear. We need to protect the fronts."

Wing adjustment (fuel saving):
  "Reduce wing by 1 notch for the fuel-saving stint. Accept 0.15 sec/lap; saves fuel consumption."

Setup change (tyre preference):
  "Tyres feeling snappy in high-speed corners. Reduce front wing 0.5 notches. Tell me if balance feels off."
```

---

## 6. RACE DECISION FRAMEWORK

### Early Race (Laps 1–10)

**Focus:** Temperature build; pace assessment

**Engineer guidance:**
- Use "standard" fuel mix (full power)
- Build tyre temperature gradually over 3–4 laps
- Assess pace vs. P2/P3 targets
- Plan first pit window: typically **lap 12–18** depending on strategy

**Radio callouts:**
```
"First lap: focus on temperature. Build smoothly; tyres ready by lap 3–4."
"Pace looks good—[X] sec up on P2. Plan pit window lap 14–16 with medium tyres."
"Conservative first stint: soft to hard. Pit lap 18; lock in track position."
```

### Mid-Race Strategic Window (Laps 10–25)

**Focus:** Pit window execution; gap management; undercut/overcut assessment

**Decision tree:**

```
IF leading AND gap > 3 sec:
  → Pit on plan (lap X); no undercut threat
  → "No pressure. Pit lap [X]. Build 4-second gap, then fuel-save."

IF gap < 3 sec AND P2 pits next lap:
  → Undercut threat; pit proactively 1–2 laps later
  → "P2 box is next lap. We'll pit lap [X+1]—gap opens via fresh tyres."

IF trailing 2–5 sec AND tyres fresh:
  → Aggressive pit strategy; softer tyres, earlier pit
  → "Plan aggressive pit lap [early_pit_lap]. Soft tyres will close the gap."

IF trailing > 5 sec AND fuel/tyres stable:
  → Conservative pit; extend stint; accept patience
  → "Tyres still good. Extend to lap [late_pit_lap]. No rush—gap is manageable."
```

### Final Stint (Laps final_stint_start–Finish)

**Focus:** Fuel criticality; tyre preservation; zero risk

**Fuel mode progression:**
1. **Laps final_stint_start–5:** Lock to **P2 lean fuel** (0.1 sec/lap cost; 3% fuel savings)
2. **Laps 5–2 before finish:** Transition to **P3 leaner fuel** (0.15 sec/lap cost; 5% fuel savings)
3. **Final 5 laps:** **P4 leanest fuel** only if gap > 3 sec and fuel margin exists

**Gap-based radio callouts:**
```
Gap > 5 sec:  "Lean fuel P3. Manage pace. 12 laps remaining—zero risk."
Gap 2–5 sec:  "P2 fuel mix; manage tyres. If gap drops below 2, prepare push."
Gap < 2 sec:  "Defend. Standard fuel mix until pit imminent. Tyres first."
Final 5 laps: "Lean fuel locked. No overtakes. Bring it home."
```

### Aggressive vs. Conservative Strategy Choice

**Aggressive choice:**
- Early pit: **Lap 12–14** (vs. planned lap 18)
- Tyre compound: Softer (soft → medium) for pace gain
- Fuel mode: Standard longer, delay fuel-saving
- Risk profile: Accept DRS vulnerability, pit traffic exposure
- When to choose: Trailing position, need to undercut, pace advantage clear

**Conservative choice:**
- Late pit: **Lap 18–20** (vs. aggressive lap 14)
- Tyre compound: Harder (soft → hard) for stability
- Fuel mode: Early fuel-saving adoption
- Risk profile: Maintain 3+ second gap; protect position
- When to choose: Leading, secure pace, track position paramount

### Overtaking Opportunity Windows

**When to attempt overtake:**
```
DRS available + gap < 1.0 sec:      "DRS active next lap. Prepare attack turn 1."
Standard overtake window:             2–4 sec gap, 3–4 corner opportunity
Committed push window:                2–4 sec gap, reserve 3–5 laps of pace

Overtake only if:
  • Tyre wear < 60%
  • Fuel buffer > 10 kg
  • Position worth the risk
  • No critical pit window imminent
```

---

## 7. ENGINEER RADIO FRAMEWORK

Use these templates as base patterns for voice response generation.

### Tyre Management Radio

```
"Tyre window opening. Prepare to box lap [window_start]–[window_end]."
"Manage the rear; ease off braking aggression. Wear is faster than expected."
"Push; gap to P2 is 2.5 sec—need 3+ before pit."
"Extend this stint 2 more laps. Tyres still have good life."
"Front tyres critical. Next pit, plan medium compound for stability."
```

### Fuel Strategy Radio

```
"Ideal mix until pit stop. Let's extend to lap [target]. Build a 2-second gap."
"Switch to P2 fuel mix. You're [gap] sec clear. We'll box lap [pit_lap]."
"15 laps remaining. Lock to lean fuel mix; manage pace."
"Fuel window tight. Box this lap; we're near the limit."
"Final 8 laps. P3 lean fuel locked in. Zero push; bring it home."
```

### Gap & Pace Radio

```
"Gap 1.8 sec—undercut vulnerable. Extend 1 lap or box this lap?"
"DRS available next lap. Prepare turn 1 attack."
"6-second gap. Stretch to 8 sec, then fuel-save aggressively."
"P2 pit is next lap. We'll box lap [X+1]. Fresh tyres gain 2.5 sec."
"You're 0.3 sec behind. Manage tyres; defend. DRS is imminent."
```

### Setup & Strategy Radio

```
"Reduce brake bias +1% rear. Fronts are wearing. Accept slight pace loss."
"Reduce wing by 1 notch for fuel saving. New stint will feel lighter."
"Pit plan unchanged: soft to medium lap [X]. Medium tyres stable from lap 8 onward."
"Track is cooling. Tyre temps will drop. Plan for earlier pit if temps drop further."
```

### Pit Stop Decisions

```
"Box this lap. Undercut is tight; fresh tyres gain 2.3 seconds."
"Stay out 1 more lap. Build gap to 2.5 sec, then box. Overcut strategy."
"Pit window is NOW. Box lap [X]. Fuel and tyres both critical."
"Delay pit 3 more laps. Tyres still good; no undercut threat; gap stable."
```

---

## 8. IMPLEMENTATION GUIDE FOR VOICE AI

### Integration with SessionState Telemetry

Map these decision frameworks to live telemetry data:

```python
# Example: Tyre wear pit trigger
driver_tyres = session_state.m_driver_data[driver_id].m_tyres
avg_wear = sum(driver_tyres.m_wear) / len(driver_tyres.m_wear)

if avg_wear > 70:
    voice_response = "Tyre window opening. Prepare to box."

# Example: Fuel pit window
current_fuel = session_state.m_driver_data[driver_id].m_fuel_in_tank
burn_rate = 1.65  # kg/lap (lean mode)
laps_remaining = current_fuel / burn_rate

if laps_remaining <= 2:
    voice_response = f"Pit window open now. Fuel limit reached in {laps_remaining:.1f} laps."

# Example: Gap-based pit strategy
gap_to_p2 = session_state.m_driver_data[leader_id].m_position - session_state.m_driver_data[driver_id].m_position
if gap_to_p2 < 1.5 and driver_tyres.avg_wear > 65:
    voice_response = "Undercut threat imminent. Box this lap—fresh tyres close the gap."
```

### System Prompt Template

```
You are an F1 race engineer providing real-time strategic advice via voice.

Use this framework for decisions:

1. Tyre wear > 70%: Suggest pit window (laps [X]–[Y])
2. Fuel < 2 laps at lean burn: Pit window OPEN
3. Gap to P2 < 1.5 sec + tyre wear > 65%: Undercut risk; pit proactively
4. Gap > 5 sec: Recommend fuel-save mode transition
5. Final 5 laps + gap secure: Lock to lean fuel; manage pace

Respond in engineer-style radio language: short, clear, actionable.
Always provide specific lap numbers and pace deltas where relevant.
```

---

## 9. REFERENCE DATA

### Circuit-Specific Notes
- **Narrow pit lanes** (Monaco, Singapore, Australia, Zandvoort): 60 km/h pit speed (vs. 80 km/h standard)
- **High-speed circuits** (Monza, Spa): Earlier pit windows; higher fuel burn; longer DRS threats
- **Low-grip circuits** (Monaco, Budapest): Softer compound deltas larger; fuel-saving modes more critical

### FIA Rules (2024)
- **Two-compound rule:** Mandatory use of minimum two slick compounds per race
- **Pit lane speed limit:** 80 km/h (60 km/h narrow circuits)
- **Pit stop minimum time:** 2.0 seconds per wheel change (4 wheels in parallel)
- **Fuel limit:** 110 kg per race; burn rate ≤ 100 kg/hour

### Common Mistakes to Avoid in Voice Responses
- ❌ Suggest pit when tyre wear is 50% (too early; unnecessary stop)
- ❌ Recommend aggressive push with <10 kg fuel margin (risk of fuel-out)
- ❌ Ignore gap-to-threat when planning undercut (timing is critical)
- ❌ Suggest setup changes mid-tyre-stint (wait for pit stop to adjust)
- ❌ Recommend DRS attack without tyre wear assessment (worn tyres slip in corners)

---

**Next Steps:**
1. Integrate `SessionState` telemetry queries into voice handler
2. Map decision trees to real-time driver data
3. Generate system prompts for LLM using these frameworks
4. Test voice responses against live F1 game telemetry
5. Iterate on engineer-style language based on feedback

