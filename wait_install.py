
import time, sys, os
log="/opt/AI-PM/install_embed.log"
deadline=time.time()+660
while time.time()<deadline:
    try:
        txt=open(log).read()
    except Exception:
        txt=""
    if "ALL DONE" in txt:
        print("STATUS=DONE")
        print(txt[-1800:])
        sys.exit(0)
    time.sleep(15)
print("STATUS=TIMEOUT")
print(open(log).read()[-1800:] if os.path.exists(log) else "no log")
