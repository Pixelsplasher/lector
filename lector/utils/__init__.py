#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
	Lector utils

	Copyright (C) 2011-2013 Davide Setti, Zdenko Podobný
	Website: http://code.google.com/p/lector

	This program is released under the GNU GPLv2

"""

import sys
import os

from glob import glob
from subprocess import Popen, PIPE
from PyQt6.QtGui import QImage

# workaroung to run textwidget outside of Lector
CMD_FOLDER = os.path.dirname(os.path.abspath(__file__))
CMD_FOLDER += "/../"
if CMD_FOLDER not in sys.path:
	sys.path.insert(0, CMD_FOLDER)

from utils import settings


def pilImage2Qt(im):
	if im.mode != 'RGB':
		im = im.convert('RGB')
	# was im.tostring
	s = im.tobytes("jpeg", "RGB")

	qtimage = QImage()
	qtimage.loadFromData(s)

#	from PIL import ImageQt
#	qtimage = ImageQt.ImageQt(im)
	return qtimage


def extract_tesseract_languages_path(error_message):
	"""
	>>> extract_tesseract_languages_path("Unable to load unicharset file /usr/share/tesseract-ocr/tessdata/invalid.unicharset")
	('/usr/share/tesseract-ocr/tessdata', '.unicharset')
	"""
	# problem if there is space in path
	print("error_message", error_message)
	if len(error_message) < 1:
		return "", ""
	invalid_path = error_message.split()[-1]
	path, invalid_fn = os.path.split(invalid_path)
	_, extension = os.path.splitext(invalid_fn)
	return path, extension

def get_tesseract_languages():
	"""
	get list of lang
	"""
	tess_exec = settings.get('tesseract-ocr:executable')
	if not tess_exec:
		tess_exec = 'tesseract'

	try:
		poTess = Popen([tess_exec, '--list-langs'],
					   shell=False, stdout=PIPE, stderr=PIPE)
		stdout_message, lTess = poTess.communicate()
		""" 
		# we need to remove not needed information e.g. OpenCL performamnce
		if isinstance(lTess, bytes):
			lTess = str(lTess, 'utf-8')
		out_split = lTess.split('\n')
		"""
		if isinstance(stdout_message, bytes):
			decoded_string = stdout_message.decode('utf-8').replace('\r\n', '\n')
			out_split = decoded_string.split('\n', 1)
			langlist = list()
			add_lang = False
			for row in out_split:
				if row.startswith('List of'):
					add_lang = True
					# added continue
					continue
				if add_lang:
					langlist.append(row.strip())
			if langlist:
				return langlist
		else:
			return get_tesseract_languages_old()
	except OSError as ex:
		print("ex", ex)
		return None

def get_tesseract_languages_old():
	"""
	make a list of installed language data files
	"""

	tess_exec = settings.get('tesseract-ocr:executable')
	if not tess_exec:
		tess_exec = 'tesseract'

	try:
		poTess = Popen([tess_exec, 'a', 'a', '-l', 'invalid'],
					   shell=False, stdout=PIPE, stderr=PIPE)
		stdout_message, lTess = poTess.communicate()
		tess_data_prefix, langdata_ext = \
										extract_tesseract_languages_path(lTess)
	except OSError as ex:
		print("ex", ex)
		return None
	# env. setting can help to handle path with spaces
	tess_data_prefix = settings.get('tesseract-ocr:TESSDATA_PREFIX:')
	if not tess_data_prefix:
		tess_data_prefix = os.getenv('TESSDATA_PREFIX')
	tessdata_path = os.path.join(tess_data_prefix, "tessdata")

	if not os.path.exists(tessdata_path):
		print("Tesseract data path ('%s') do not exist!" % tessdata_path)
		return None
	langdata = glob(tess_data_prefix + os.path.sep + '*' + langdata_ext)
	return [os.path.splitext(os.path.split(uc)[1])[0] for uc in langdata]

def get_spellchecker_languages(directory = None):
	"""
	Check if spellchecker is installed and provide list of languages
	"""
	try:
		import enchant

		if (directory):
			enchant.set_param("enchant.myspell.dictionary.path", directory)
		langs = enchant.list_languages()
		return sorted(langs)

	except:
		print("can not start spellchecker!!!")
		import traceback
		traceback.print_exc()
		return None


# for testing module funcionality
def main():
	""" Main loop to run test
	"""
	# langs = get_spellchecker_languages()
	langs = get_tesseract_languages()
	if langs:
		print('Found languages:', langs)
	else:
		print('No lang found!')
	return

if __name__ == '__main__':
	main()
