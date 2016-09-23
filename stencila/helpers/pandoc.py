import subprocess
import tempfile

class Pandoc:
    """
    Helps with Pandoc workflow tasks
    """

    def call(self, args, input=None):
        """
        Call Pandoc
        """
        process = subprocess.Popen(
            ['pandoc'] + list(args),
            stdin=subprocess.PIPE if input else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = process.communicate(input=input)
        # Decode bytes to unicode
        out = out.decode('utf8')
        err = err.decode('utf8')
        if process.returncode:
            raise RuntimeError('Error calling Pandoc\n  return code: %s\n  message: %s\n  arguments: %s' % (process.returncode, err, args))
        else:
            return out

    def read_options(self, format):
        options = {
            'md': '--from markdown_github'
        }.get(format, '--from ' + format)
        return options.split()

    def write_options(self, format):
        options = {
            'md': '--to markdown_github'
        }.get(format, '--to ' + format)
        return options.split()

    def options(self, fro, to):
        return self.read_options(fro) + self.write_options(to)

    def convert(self, content, fro, to):
        return self.call(self.options(fro, to), input=content)

    def read(self, path, fro, to):
        return self.call(self.options(fro, to) + [path])

    def write(self, content, path, fro, to):
        with tempfile.NamedTemporaryFile() as temp:
            temp.write(content)
            temp.flush()
            self.call(self.options(fro, to) + ['--output', path, temp.name])


pandoc = Pandoc()
