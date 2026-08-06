import os, paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("81.70.158.130", port=7000, username="root", password=os.environ["AIPM_PASS"], timeout=25)
sftp = c.open_sftp()

# Clean remote dist first to avoid stale files
_, out, _ = c.exec_command("rm -rf /opt/AI-PM/frontend/dist")
out.read()

# Upload new dist
local_dist = os.path.join(os.getcwd(), "frontend", "dist")
remote_dist = "/opt/AI-PM/frontend/dist"
count = 0
for root, dirs, files in os.walk(local_dist):
    for f in files:
        local_file = os.path.join(root, f)
        rel = os.path.relpath(local_file, local_dist).replace(os.sep, "/")
        remote_file = f"{remote_dist}/{rel}"
        # Make sure remote directory exists
        remote_dir = os.path.dirname(remote_file)
        parts = remote_dir.strip("/").split("/")
        cur = ""
        for p in parts:
            cur += "/" + p
            try:
                sftp.stat(cur)
            except:
                try:
                    sftp.mkdir(cur)
                except:
                    pass
        sftp.put(local_file, remote_file)
        count += 1
print(f"uploaded {count} files")

_, out, _ = c.exec_command('curl -sk -m 10 -o /dev/null -w "%{http_code}" https://aipm.twzx.bj.cn/')
print("Domain health:", out.read().decode().strip())

# Verify the fix is in the new bundle
_, out, _ = c.exec_command("grep -c useLocation /opt/AI-PM/frontend/dist/assets/*.js 2>/dev/null | grep -v ':0' | head -5")
print("Files containing useLocation:")
print(out.read().decode().strip())

sftp.close()
c.close()
print("OK")
