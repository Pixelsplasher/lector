#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Lector: spellchecker.py
    Copyright (C) 2009, John Schember

    Modified for Lector by Zdenko Podobný
    This code is released under MIT licence
"""

import re

# No module named 'PyQt6.Qt'
# QAction has moved to PyQt6.QtGui
from PyQt6.QtCore import Qt
# QSyntaxHighlighter, QTextCharFormat moved from PyQt6.QtCore to PyQt6.QtGui
from PyQt6.QtGui import QAction, QColor, QSyntaxHighlighter, QTextCharFormat
# No module named 'PyQt6.Qt'
from PyQt6.QtCore import pyqtSignal

class Highlighter(QSyntaxHighlighter):

    WORDS = u'(?iu)[\w\']+'

    def __init__(self, *args):
        QSyntaxHighlighter.__init__(self, *args)

        self.dict = None

    def setDict(self, dict):
        self.dict = dict

    def highlightBlock(self, text):
        if not self.dict:
            return

        format = QTextCharFormat()
		# was Qt.red
        format.setUnderlineColor(Qt.GlobalColor.red)
		# was QTextCharFormat.SpellCheckUnderline
        format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)

        for word_object in re.finditer(self.WORDS, text):
            if not self.dict.check(word_object.group()):
                self.setFormat(word_object.start(),
                    word_object.end() - word_object.start(), format)


class SpellAction(QAction):
    '''
    A special QAction that returns the text in a signal.
    '''

    correct = pyqtSignal()

    def __init__(self, *args):
        QAction.__init__(self, *args)

        self.triggered.connect(lambda x: self.correct.emit(self.text()))
