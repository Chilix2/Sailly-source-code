# Live Call Issues — Summary Report (April 20, 2026)

## Test Call: demo-9f97d6c28066 @ 10:46-10:48 UTC

### Issues Reported by User
1. **"kein roboterhafter klang" being said at end of messages** → FIXED
2. **Barge-in not working when bot is speaking** → INVESTIGATING
3. **create_order failed with send_sms issue** → PARTIALLY FIXED (send_sms now correctly blocks, but order still fails)

---

## Issue-by-Issue Status

### Issue 1: TTS Artifact "kein roboterhafter klang" ✅ FIXED

**Status**: FIXED (service restarted 10:54 UTC)

**Root Cause**: The phrase "Kein roboterhafter Klang" was in the TTS style prompt at `server/main.py:58`. This is a meta-instruction for Gemini's style guidance, but Gemini's TTS API was including it in the audio output.

**Fix Applied**:
```python
# BEFORE
CASCADE_TTS_STYLE_PROMPT = (
    "Sprich natürlich, klar und in zügigem, freundlichem Tempo auf Deutsch — "
    "wie an einer Restaurant-Rezeption. Kein roboterhafter Klang."
)

# AFTER
CASCADE_TTS_STYLE_PROMPT = (
    "Sprich natürlich, klar und in zügigem, freundlichem Tempo auf Deutsch — "
    "wie an einer Restaurant-Rezeption."
)
```

**Verification**: Next call should NOT include this phrase in audio output.

---

### Issue 2: Barge-in Not Working ⏳ INVESTIGATING

**Status**: Handler properly wired, root cause unknown

**Findings**:
- ✅ `BargeInHandler` class exists in `server/barge_in_handler.py:19`
- ✅ Imported in `server/main.py:43`
- ✅ Instantiated at line 335
- ✅ Wired in Pipecat pipeline at line 346

**Possible Root Causes**:
1. Suppress flag not properly toggling after greeting
2. Handler not receiving transcription frames during bot speech
3. STT frames not reaching handler due to pipeline order

**Next Investigation**:
- Monitor logs for barge-in handler messages during next call
- Check if `suppress_barge_in_during_greeting` flag transitions properly
- Verify STT→BargeInHandler→Brain pipeline connectivity

---

### Issue 3: create_order Fails with total_price=0.0 ⏳ PARTIALLY FIXED

**Status**: Fix 2 working, Fix 3 not firing

**What's Working** ✅:
- Fix 1 (Menu Caching): ✅ CONFIRMED — logs show "[MENU_CACHE] cached 7 items"
- Fix 2 (send_sms Guard): ✅ CONFIRMED — send_sms correctly blocked when create_order failed

**What's NOT Working** ❌:
- Fix 3 (Price Fallback): ❌ NOT FIRING — no "[create_order] price fallback" log entry

**Debug Output Awaited**:
Added verbose logging to pinpoint exact failure point on next call.

---

## Changes Deployed This Session

1. **TTS Artifact Fix**: Removed problematic phrase from style prompt
2. **Debug Logging**: Added throughout price fallback chain to diagnose Issue 3
3. **Service**: Restarted at 10:54 UTC

---

## Next Action: Test Call Required

Please make a test call to verify fixes and capture debug output for Issue 3 diagnosis.

