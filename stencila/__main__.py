import time
import stencila

print 'Running Stencila at %s/?token=%s. Use Ctrl+C to exit\n' % (stencila.instance.url(), stencila.instance.token)
while True:
    try:
        time.sleep(0x7FFFFFFF)
    except KeyboardInterrupt:
        break
