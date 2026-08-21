import subprocess
import tempfile
import base64

with tempfile.NamedTemporaryFile() as f:
    print('base64 encoded exploit: ', flush=True)
    data = input().encode()

    f.write(base64.b64decode(data))
    f.flush()

    subprocess.check_call(['/home/ctf/d8', f.name])
