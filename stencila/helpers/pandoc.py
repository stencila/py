import subprocess


class Pandoc:
    """
    Helps with Pandoc workflow tasks
    """

    def __call__(self, *args):
        """
        Call Pandoc
        """
        process = subprocess.Popen(
            ['pandoc'] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = process.communicate()
        if process.returncode:
            raise RuntimeError('Error calling Git\n  return code: %s\n  message: %s\n  arguments: %s' % (process.returncode, err, args))
        else:
            return out

pandoc = Pandoc()
