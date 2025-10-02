#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Lector: lector.py

	Copyright (C) 2011-2014 Davide Setti, Zdenko Podobný
	Website: http://code.google.com/p/lector

	This program is released under the GNU GPLv2
"""
#pylint: disable-msg=C0103

# System
import sys
import os
from PyQt6.QtGui import QIcon
# qsrand is deprecated/obsolete in modern Qt versions (since Qt 5.10)
import random
# added Qt, QByteArray
from PyQt6.QtCore import (Qt, QSettings, QPoint, QSize, QTime, pyqtSlot,
						  QLocale, QTranslator, QByteArray)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDialog, QFileDialog,
							 QMessageBox)

# Lector
from ui.ui_lector import Ui_Lector
from settingsdialog import Settings
from ocrwidget import QOcrWidget
from editor.textwidget import TextWidget, EditorBar
from utils import get_tesseract_languages
from utils import settings

__version__ = "1.0.0dev"


class Window(QMainWindow):
	""" MainWindow
	"""
	ocrAvailable = True
	thread = None

	def __init__(self, hasScanner=True):
		QMainWindow.__init__(self)

		self.curDir = ""
		self.ui = Ui_Lector()
		self.ui.setupUi(self)

		self.ocrWidget = QOcrWidget("eng", 1, self.statusBar())

		self.textEditor = TextWidget()
		self.textEditorBar = EditorBar()
		self.textEditorBar.saveDocAsSignal.connect(self.textEditor.saveAs)
		self.textEditorBar.spellSignal.connect(self.textEditor.toggleSpell)
		self.textEditorBar.whiteSpaceSignal.connect(
			self.textEditor.togglewhiteSpace)
		self.textEditorBar.boldSignal.connect(self.textEditor.toggleBold)
		self.textEditorBar.italicSignal.connect(self.textEditor.toggleItalic)
		self.textEditorBar.underlineSignal.connect(
			self.textEditor.toggleUnderline)
		self.textEditorBar.strikethroughSignal.connect(
			self.textEditor.toggleStrikethrough)
		self.textEditorBar.subscriptSignal.connect(
			self.textEditor.toggleSubscript)
		self.textEditorBar.superscriptSignal.connect(
			self.textEditor.toggleSuperscript)
		self.textEditor.fontFormatSignal.connect(
			self.textEditorBar.toggleFormat)

		self.ui.mwTextEditor.addToolBar(self.textEditorBar)
		self.ui.mwTextEditor.setCentralWidget(self.textEditor)
		self.ocrWidget.textEditor = self.textEditor

		self.setCentralWidget(self.ocrWidget)

		self.ui.actionRotateRight.triggered.connect(self.ocrWidget.rotateRight)
		self.ui.actionRotateLeft.triggered.connect(self.ocrWidget.rotateLeft)
		self.ui.actionRotateFull.triggered.connect(self.ocrWidget.rotateFull)
		self.ui.actionZoomIn.triggered.connect(self.ocrWidget.zoomIn)
		self.ui.actionZoomOut.triggered.connect(self.ocrWidget.zoomOut)
		self.ui.actionOcr.triggered.connect(self.ocrWidget.doOcr)
		self.ocrWidget.scene().changedSelectedAreaType.connect(
			self.changedSelectedAreaType)

		try:
			languages = list(get_tesseract_languages())
		except TypeError:  # tesseract is not installed
			# TODO: replace QMessageBox.warning with QErrorMessage (but we need
			#	  to keep state
			# dialog = QErrorMessage(self)
			# dialog.showMessage(
			#	self.tr("tessaract not available. Please check requirements"))
			QMessageBox.warning(self, "Tesseract",
								self.tr("Tessaract is not available. "
										"Please check requirements."))
			self.ocrAvailable = False
			self.on_actionSettings_triggered(2)
		else:
			languages.sort()

			languages_ext = {
				'bul': self.tr('Bulgarian'),
				'cat': self.tr('Catalan'),
				'ces': self.tr('Czech'),
				'chi_tra': self.tr('Chinese (Traditional)'),
				'chi_sim': self.tr('Chinese (Simplified)'),
				'dan': self.tr('Danish'),
				'dan-frak': self.tr('Danish (Fraktur)'),
				'nld': self.tr('Dutch'),
				'eng': self.tr('English'),
				'fin': self.tr('Finnish'),
				'fra': self.tr('French'),
				'deu': self.tr('German'),
				'deu-frak': self.tr('German (Fraktur)'),
				'ell': self.tr('Greek'),
				'hun': self.tr('Hungarian'),
				'ind': self.tr('Indonesian'),
				'ita': self.tr('Italian'),
				'jpn': self.tr('Japanese'),
				'kor': self.tr('Korean'),
				'lav': self.tr('Latvian'),
				'lit': self.tr('Lithuanian'),
				'nor': self.tr('Norwegian'),
				'pol': self.tr('Polish'),
				'por': self.tr('Portuguese'),
				'ron': self.tr('Romanian'),
				'rus': self.tr('Russian'),
				'slk': self.tr('Slovak'),
				'slk-frak': self.tr('Slovak (Fraktur)'),
				'slv': self.tr('Slovenian'),
				'spa': self.tr('Spanish'),
				'srp': self.tr('Serbian'),
				'swe': self.tr('Swedish'),
				'swe-frak': self.tr('Swedish (Fraktur)'),
				'tgl': self.tr('Tagalog'),
				'tur': self.tr('Turkish'),
				'ukr': self.tr('Ukrainian'),
				'vie': self.tr('Vietnamese')
				}

			for lang in languages:
				try:
					lang_ext = languages_ext[lang]
				except KeyError:
					continue

				self.ui.rbtn_lang_select.addItem(lang_ext, lang)
				self.ui.rbtn_lang_select.currentIndexChanged.connect(
					self.changeLanguage)

		#disable useless actions until a file has been opened
		self.enableActions(False)

		## load saved settings
		self.readSettings()

		self.ui.actionScan.setEnabled(False)
		if hasScanner:
			self.on_actionChangeDevice_triggered()
		if not self.statusBar().currentMessage():
			self.statusBar().showMessage(self.tr("Ready"), 2000)

	@pyqtSlot()
	def on_actionChangeDevice_triggered(self):
		##SANE
		message = ''
		try:
			import sane
		except ImportError:
			# sane found no scanner - disable scanning;
			message = self.tr("Sane not found! Scanning is disabled.")
		else:
			from .scannerselect import ScannerSelect
			sane.init()
			sane_list = sane.get_devices()
			saved_device = settings.get('scanner:device')
			if saved_device in [x[0] for x in sane_list]:
				message = self.tr("Sane found configured device...")
				self.scannerSelected()
			elif not sane_list:
				message = self.tr("Sane dit not find any device! "
								  "Scanning is disabled.")
			else:
				# there is not configured device => run configuration
				ss = ScannerSelect(sane_list, parent=self)
				ss.accepted.connect(self.scannerSelected)
				ss.show()
		self.statusBar().showMessage(message, 2000)

	def scannerSelected(self):
		self.ui.actionScan.setEnabled(True)

		if self.thread is None:
			from .scannerthread import ScannerThread

			self.thread = ScannerThread(self, settings.get('scanner:device'))
			self.thread.scannedImage.connect(self.on_scannedImage)

	def on_scannedImage(self):
		self.ocrWidget.scene().im = self.thread.im
		fn = self.tr("Unknown")
		self.ocrWidget.filename = fn
		self.ocrWidget.prepareDimensions()
		self.setWindowTitle("Lector: " + fn)
		self.enableActions()

	@pyqtSlot()
	def on_actionSettings_triggered(self, tabIndex = 0):
		settings_dialog = Settings(self, tabIndex)
		settings_dialog.accepted.connect(self.updateTextEditor)
		settings_dialog.show()

	def updateTextEditor(self):
		self.textEditor.setEditorFont()

	@pyqtSlot()
	def on_actionOpen_triggered(self):
		fn, _ = QFileDialog.getOpenFileName(self,
				self.tr("Open image"), self.curDir,
				self.tr("Images (*.tif *.tiff *.png *.jpg *.xpm)")
			 )
		if not fn: return

		self.ocrWidget.filename = fn
		self.curDir = os.path.dirname(fn)
		self.ocrWidget.changeImage()
		self.setWindowTitle("Lector: " + fn)

		self.enableActions(True)

	def enableActions(self, enable=True):
		for action in (self.ui.actionRotateRight,
					   self.ui.actionRotateLeft,
					   self.ui.actionRotateFull,
					   self.ui.actionZoomIn,
					   self.ui.actionZoomOut,
					   self.ui.actionSaveDocumentAs,
					   self.ui.actionSaveImageAs,):
			action.setEnabled(enable)
		self.ui.actionOcr.setEnabled(enable and self.ocrAvailable)

	@pyqtSlot()
	def on_actionScan_triggered(self):
		self.thread.run()
		##TODO: check thread end before the submission of a new task
		#self.thread.wait()

	def changeLanguage(self, row):
		lang = self.sender().itemData(row)
		self.ocrWidget.language = lang

	@pyqtSlot()
	def on_rbtn_text_clicked(self):
		self.ocrWidget.areaType = 1

	@pyqtSlot()
	def on_rbtn_image_clicked(self):
		self.ocrWidget.areaType = 2

	# clicking the change box type events
	# from image type to text
	# or from text type to image
	@pyqtSlot()
	def on_rbtn_areato_text_clicked(self):
		self.ocrWidget.scene().changeSelectedAreaType(1)

	@pyqtSlot()
	def on_rbtn_areato_image_clicked(self):
		self.ocrWidget.scene().changeSelectedAreaType(2)

	def readSettings(self):
		""" Read settings
		"""
		setting = QSettings("Davide Setti", "Lector")
		pos = setting.value("pos", QPoint(50, 50))
		size = setting.value("size", QSize(800, 500))
		self.curDir = setting.value("file_dialog_dir", '~/')
		self.resize(size)
		self.move(pos)
		# added next 2 lines to avoid: argument 1 has unexpected type 'NoneType' error
		geometry = setting.value("mainWindowGeometry")
		if geometry is not None and isinstance(geometry, (QByteArray, bytes, bytearray)):
			self.restoreGeometry(setting.value("mainWindowGeometry"))
			self.restoreState(setting.value("mainWindowState"))

		## load saved language
		lang = setting.value("rbtn/lang", "")
		try:
			currentIndex = self.ui.rbtn_lang_select.findData(lang)
			self.ui.rbtn_lang_select.setCurrentIndex(currentIndex)
			self.ocrWidget.language = lang
		except KeyError:
			pass

	def writeSettings(self):
		""" Store settings
		"""
		settings.set("pos", self.pos())
		settings.set("size", self.size())
		settings.set("file_dialog_dir", self.curDir)
		settings.set("mainWindowGeometry", self.saveGeometry())
		settings.set("mainWindowState", self.saveState())

		## save language
		settings.set("rbtn/lang", self.ocrWidget.language)

	def closeEvent(self, event):
		""" Action before closing app
		"""
		if (not self.ocrWidget.scene().isModified) or self.areYouSureToExit():
			self.writeSettings()
			event.accept()
		else:
			event.ignore()

	def areYouSureToExit(self):
		# was QMessageBox.AttributeName
		""" ret = QMessageBox(self.tr("Lector"),
					 self.tr("Are you sure you want to exit?"),
					 QMessageBox.Icon.Warning,
					 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Default,
					 QMessageBox.StandardButton.No | QMessageBox.StandardButton.Escape,
					 QMessageBox.StandardButton.NoButton)
		"""
		ret = QMessageBox(QMessageBox.Icon.Warning,
					self.tr("Lector"),
					self.tr("Are you sure you want to exit?"),
					QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
					self,
					Qt.WindowType.Dialog|Qt.WindowType.MSWindowsFixedSizeDialogHint)
		ret.setWindowIcon(QIcon(":/icons/icons/L.png"))
		# 'QMessageBox' object has no attribute 'setButtonText' bug ???
		# ret.setButtonText(QMessageBox.StandardButton.Yes, self.tr("Yes"))
		# ret.setButtonText(QMessageBox.StandardButton.No, self.tr("No"))
		return ret.exec() == QMessageBox.StandardButton.Yes

	@pyqtSlot()
	def on_actionSaveDocumentAs_triggered(self):
		self.textEditor.saveAs()

	@pyqtSlot()
	def on_actionSaveImageAs_triggered(self):
		fn = str(QFileDialog.getSaveFileName(self,
						self.tr("Save image"), self.curDir,
						self.tr("PNG image (*.png);;"
								"TIFF image (*.tif *.tiff);;"
								"BMP image (*.bmp)")
						))
		if not fn:
			return

		self.curDir = os.path.dirname(fn)
		## TODO: move this to the Scene?
		self.ocrWidget.scene().im.save(fn)

	@pyqtSlot()
	def on_actionAbout_Lector_triggered(self):
		QMessageBox.about(self, self.tr("About Lector"), self.tr(
		  "<p>The <b>Lector</b> is a graphical ocr solution for GNU/"
		  "Linux and Windows based on Python, Qt4 and tessaract OCR.</p>"
		  "<p>Scanning option is available only on GNU/Linux via SANE.</p>"
		  "<p></p>"
		  "<p><b>Author:</b> Davide Setti</p><p></p>"
		  "<p><b>Contributors:</b> chopinX04, filip.dominec, zdposter</p>"
		  "<p><b>Web site:</b> http://code.google.com/p/lector</p>"
		  "<p><b>Source code:</b> "
		  "http://sourceforge.net/projects/lector-ocr/</p>"
		  "<p><b>Version:</b> %s</p>" % __version__)
		  )

	def changedSelectedAreaType(self, _type):
		if _type in (1, 2):
			self.ui.rbtn_areato_text.setCheckable(True)
			self.ui.rbtn_areato_image.setCheckable(True)

			if _type == 1:
				self.ui.rbtn_areato_text.setChecked(True)
			else: #_type = 2
				self.ui.rbtn_areato_image.setChecked(True)
		else:
			self.ui.rbtn_areato_text.setCheckable(False)
			self.ui.rbtn_areato_text.update()
			self.ui.rbtn_areato_image.setCheckable(False)
			self.ui.rbtn_areato_image.update()


## MAIN
def main():
	if settings.get('log:errors'):
		log_filename = settings.get('log:filename')
		if log_filename:
			try:
				log_file = open(log_filename,"w")
				print ('Redirecting stderr/stdout... to %s' % log_filename)
				sys.stderr = log_file
				sys.stdout = log_file
			except IOError:
				print("Lector could not open log file '%s'!\n" % log_filename \
					  + " Redirecting will not work.")
		else:
			print("Log file is not set. Please set it in settings.")

	app = QApplication(sys.argv)
	opts = [str(arg) for arg in app.arguments()[1:]]
	if '--no-scanner' in opts:
		scanner = False
	else:
		scanner = True
	
	random.seed()
	# qsrand(QTime(0, 0, 0).secsTo(QTime.currentTime()))

	locale = settings.get('ui:lang')
	if not locale:
		locale = QLocale.system().name()
	qtTranslator = QTranslator()
	if qtTranslator.load(":/translations/ts/lector_" + locale, 'ts'):
		app.installTranslator(qtTranslator)

	window = Window(scanner)
	window.show()
	app.exec()

if __name__ == "__main__":
	main()
