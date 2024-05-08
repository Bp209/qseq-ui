from .timestamp import QSEQ_TIMESTAMP


class CsvLog(object):
    def __init__(self, filename=None):
        self.use_stdout = False
        self.known_headers = list()
        if filename is None:
            self.use_stdout = True
        else:
            self.fd = open(filename, 'w')

    def _write_csv(self, *items):
        new_items = list()
        for i in map(str, items):
            if ',' in i:
                i = i.replace('\\', '\\\\')
                i = i.replace('"', '\\"')
                i = '"%s"' % i
            new_items.append(i)

        text = ','.join(new_items)
        if self.use_stdout:
            print(text)
        else:
            self.fd.write(text)

    def header(self, modname, *items):
        if modname not in self.known_headers:
            self._write_csv(modname, 'HEADER', *items)
            self.known_headers.append(modname)

    def write(self, modname, *items):
        self._write_csv(modname, '%.6f' % QSEQ_TIMESTAMP(), *items)
