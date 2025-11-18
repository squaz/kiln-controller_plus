# Kiln Controller – Logging Documentation  
## (ziplogs_journal usage + internal logging architecture)

---

# 📄 1. ziplogs_journal – Log Extraction & CSV Export

## Overview

`ziplogs_journal` is a custom log-extraction tool created for this Raspberry Pi kiln-controller system.  
It collects logs from **systemd’s journal** and exports them as **CSV files**, separated per day for easy analysis and long-term archiving.

This script is necessary because the Raspberry Pi installation **does not write kiln logs to `/var/log/daemon.log` or `/var/log/syslog`**, but instead stores them inside **systemd-journald**, which requires `journalctl` to read.

This document explains:

- why this script is required  
- how it works  
- where logs come from  
- how to use it  
- how output is structured for Google Sheets  

---

## Why this script is needed

### 🔹 1. kiln-controller logs are not in `/var/log/daemon.log`

Most Raspberry Pi systems used for tutorials still rely on rsyslog and produce plain-text logs:

/var/log/syslog
/var/log/daemon.log


However, modern installations (like yours) use **systemd-journald only**, meaning:

- `/var/log/daemon.log` does not exist
- `/var/log/syslog` does not exist
- logs are stored in **binary form** at:

/var/log/journal/


These cannot be processed by the original `ziplogs` script.

### 🔹 2. kiln logs must be spreadsheet-friendly

kiln-controller prints detailed log entries for temperature control, PID parameters, heater status, and runtime values. Example:

2025-10-14T12:34:56.789012+0200 kiln python[350]: 2025-10-14 12:34:56,824 INFO oven: temp=1021.40 target=1025.00 error=3.60 ...

markdown
Code kopieren

This is good for humans but very hard to analyze later.

`ziplogs_journal` converts these into a CSV with columns:

- `journal_ts`
- `app_ts`
- `level`
- `logger`
- `message`

Which is perfect for Google Sheets.

### 🔹 3. Logs should be split by firing day

Most kiln runs happen over many hours or even days apart.  
To stay organized, we generate:

extracted_logs/kiln-YYYY-MM-DD.csv.gz

yaml
Code kopieren

This allows comparisons between different firings and long-term tracking.

---

## What the script does

### ✔ Reads logs from systemd’s journal

Using:

journalctl -u kiln-controller.service -o short-iso --no-pager


This retrieves **everything ever logged by kiln-controller**, even across reboots.

### ✔ Filters relevant kiln log lines

Specifically INFO/WARN/ERROR from:

- oven
- kiln-controller
- gevent

### ✔ Parses log lines to extract fields  
### ✔ Splits logs by their date  
### ✔ Writes CSV with a header row  
### ✔ Compresses each file into `.csv.gz`

---

## How to use the script

### 1️⃣ Extract ALL logs (auto-split per day)

./ziplogs_journal

Produces files such as:

extracted_logs/kiln-2025-10-14.csv.gz
extracted_logs/kiln-2025-10-20.csv.gz


### 2️⃣ Extract logs for ONE specific day

European format:

./ziplogs_journal 14.10.2025

ISO format:

./ziplogs_journal 2025-10-14


Output:

extracted_logs/kiln-2025-10-14.csv.gz

---

## Importing CSV into Google Sheets

1. Copy the file to your PC  
2. Unzip:

gzip -d kiln-2025-10-14.csv.gz


3. In Google Sheets:  
   **File → Import → Upload → Choose File → Separator: Comma**

You can now filter by level, time, logger, or temperature fields.

---

# 📄 2. INTERNAL LOGGING ARCHITECTURE (How kiln-controller creates logs)

This chapter explains **how logs are generated inside the kiln-controller codebase**, so future you understands exactly where the data comes from, and why it appears the way it does.

---

## 🔥 Where logs originate in the code

Logging is primarily created in three locations:

1. `lib/oven.py`
2. `kiln-controller.py`
3. `OvenWatcher` (real-time WebSocket state push)

---

## 1. Logging inside `oven.py` (🔥 MOST IMPORTANT)

`oven.py` contains the **PID control loop** that runs every 2 seconds.  
At the end of each cycle, it logs a full temperature control summary including:

- current temperature
- target temperature
- PID error
- proportional/integral/derivative contributions
- heater on/off durations
- runtime and schedule timing

A typical cycle log looks like:

INFO oven: temp=1021.40 target=1025.00 error=3.60 pid=67.23 p=14.40 i=49.81 d=3.02 heat_on=1.20 heat_off=0.80 run_time=3530 total_time=3600 time_left=70


This is the core of your daily log export.

---

## 2. Logging inside kiln-controller.py

This file:

- starts the webserver  
- loads profiles  
- adds/removes observers  
- reports state transitions  

Typical logs here include:

INFO kiln-controller: Starting controller
INFO kiln-controller: Loading profile test-fast.json
INFO kiln-controller: Switching to RUNNING
WARN kiln-controller: Attempt to start already-running kiln

yaml
Code kopieren

These are operational logs rather than temperature logs.

---

## 3. Logging inside OvenWatcher

The `OvenWatcher` watches:

- temperature updates
- state transitions
- error conditions

It also streams logs over WebSocket (`/status`), but **these are not written to disk** unless captured by a client such as:

- kiln-logger.py  
- your new ziplogs_journal  

---

## 🔧 How logging is configured

All logging uses Python’s `logging` module.  
kiln-controller configures logging early in startup using:

logging.basicConfig(level=config.log_level, format=config.log_format)

sql
Code kopieren

Logs are emitted via:

log.info("...")
log.warn("...")
log.error("...")

yaml
Code kopieren

Then:

- systemd collects stdout/stderr  
- stores them in its journal  
- `journalctl -u kiln-controller.service` retrieves them  

The old `/var/log/daemon.log` is NOT used unless rsyslog is installed.

---

## 🧠 Data flow summary

### Inside kiln-controller:

oven cycle → log.info(...) → stdout → systemd-journald → journalctl

shell
Code kopieren

### Your script:

journalctl → filter → parse → daily CSV → compressed → archived


### Your analysis:

CSV → Google Sheets → filtering/graphs/statistics

---

# 📄 3. Summary

### The kiln-controller logging system:

- produces two main log types:
  - **temperature/PID cycle logs**
  - **operational system logs**
- stores all logs inside **systemd-journald**
- does NOT use `/var/log/syslog` or `/var/log/daemon.log`
- is now fully exportable using your `ziplogs_journal` script
- outputs logs in spreadsheet-friendly CSV format
- automatically splits logs per firing day

### The new workflow:

1. Run firings normally  
2. Extract logs whenever needed  
3. Import CSV into Sheets  
4. Filter, analyze, compare firings  
5. Long-term archive stays clean and organized  

This allows highly accurate firing analysis and performance evaluation across months or years.

---

# End of File