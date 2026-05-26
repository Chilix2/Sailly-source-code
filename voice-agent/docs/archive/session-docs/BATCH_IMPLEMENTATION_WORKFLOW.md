# Batch Implementation Workflow

## Standard Procedure for All Batches

To prevent wasting time debugging fixes that are already implemented but not deployed, the following workflow is MANDATORY:

### 1. Implement Code Changes
- Read existing code sections
- Make targeted fixes per batch plan
- Run linter checks
- Mark todos as in_progress → completed

### 2. **CRITICAL: Restart Service AFTER Each Batch**
Always restart the service to load the latest code changes into memory:

```bash
# Kill current service
sudo systemctl stop sailly-browser-demo.service
sleep 2

# Restart with latest batch
sudo systemctl start sailly-browser-demo.service
sleep 5

# Verify it's running
sudo systemctl status sailly-browser-demo.service
```

### 3. Test with New Call Reports
Only AFTER service restart, run new test calls and collect call reports to verify fixes work.

### 4. Never Skip the Restart
The Python FastAPI process runs in memory. Code changes in files are NOT loaded until the process is restarted. Without restart:
- All testing is against stale code
- Bugs appear to still exist even though they're fixed
- Debugging effort is wasted on already-solved issues

## Why This Matters

Example: Batch 08 implementation
- ✅ Code fixes committed to files at ~3:15 AM UTC
- ❌ Service NOT restarted
- ❌ Calls made 14:00-14:36 UTC still failed (13+ hours later)
- 🔄 Wasted time debugging "failures" that were already fixed

After restart at 14:45 UTC:
- ✅ Fixes are now live and active

## Service Commands Reference

```bash
# Stop (graceful shutdown)
sudo systemctl stop sailly-browser-demo.service

# Start
sudo systemctl start sailly-browser-demo.service

# Restart (stop + start)
sudo systemctl restart sailly-browser-demo.service

# Check status
sudo systemctl status sailly-browser-demo.service

# View logs
sudo journalctl -u sailly-browser-demo.service -n 50 --no-pager
```

## Batch Checklist Template

```
- [ ] Read code sections (plan reference)
- [ ] Implement Fix 1 (description)
- [ ] Implement Fix 2 (description)
- [ ] Run linter checks (no errors)
- [ ] Mark todos completed
- [ ] **RESTART SERVICE** ← DO NOT SKIP
- [ ] Verify service is running (journalctl confirms startup)
- [ ] Run test calls and collect new reports
- [ ] Verify fixes work in call reports
```
