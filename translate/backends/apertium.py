# -*- coding: utf-8 -*-

from translate.backend import IBackend

import subprocess
import logging
import re

log = logging.getLogger(__name__)


class ApertiumBackend(IBackend):
    name = "Apertium"
    description = "A free/open-source machine translation platform"
    preference = 20

    def __init__(self):
        try:
            self.exe = subprocess.check_output(['which', 'apertium']).strip()

            self.pairs = set()

            for pair in subprocess.check_output(['apertium', '-l']).split():
                self.pairs.add(re.search('(.*?)-([^_-]*)', pair).groups())

            self.pairs = list(self.pairs)

        except subprocess.CalledProcessError:
            assert False
            self.preference = -1
            self.pairs = []
            log.warning("apertium not available, ignoring...")

    def translate(self, text, from_lang, to_lang):
        proc = subprocess.Popen(['apertium',
                                 '{0}-{1}'.format(from_lang, to_lang)],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        proc.stdin.write(text + '\n')
        proc.stdin.close()
        return proc.stdout.read()

    def language_pairs(self):
        return self.pairs
