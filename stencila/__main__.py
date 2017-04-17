import time
import stencila

stencila.host.start()
while True:
    try:
        time.sleep(0x7FFFFFFF)
    except KeyboardInterrupt:
        break
