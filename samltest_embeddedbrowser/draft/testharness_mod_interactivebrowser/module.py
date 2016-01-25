import sys
from PyQt4.QtGui import QApplication,  QGridLayout, QWidget, QPushButton
from PyQt4.QtWebKit import QWebView
try:
    from PyQt4.QtCore import QString
except ImportError:
    # we are using Python3 so QString is not defined
    QString = type("")

from .injector import InjectedQNetworkRequest, InjectedQNetworkAccessManager
from .gui import UrlInput
#import path

"""

	TestAction displays the resonse from urllib and takes over the
	handling in an embedded browser.

	__init__ takes an AutoCloseUrls object, which can hold URLs and
	http status codes, to automagically stop the process returning a
	defined result.

	run takes the response object from urllib2 and the corresponding
	url for that response.

"""


class TestAction(object):

	def __init__(self,autocloseurls=None):
		self.autocloseurls = autocloseurls

	def run(self,urllib_response,request_url):
		self.retval = False


		request = InjectedQNetworkRequest(request_url)

		nam = InjectedQNetworkAccessManager()
		nam.setInjectedResponse(urllib_response)
		nam.setAutoCloseUrls(self.autocloseurls)

		nam.autocloseOk.connect(self.button_ok)

		app = QApplication([])
		grid = QGridLayout()
		browser = QWebView()

		page = browser.page()
		page.setNetworkAccessManager(nam)

		browser.load(request, nam.GetOperation)



		test_ok_button = QPushButton("Test &OK")
		test_ok_button.clicked.connect(self.button_ok)

		test_failed_button = QPushButton("Test &Failed")
		test_failed_button.clicked.connect(self.button_failed)

		url_input = UrlInput(browser)

		grid.addWidget(test_ok_button, 1, 0)
		grid.addWidget(test_failed_button, 1, 1)
		grid.addWidget(url_input, 2, 0, 1, 2)
		grid.addWidget(browser, 4, 0, 1, 2)

		main_frame = QWidget()
		main_frame.setLayout(grid)
		main_frame.show()

		app.exec_()
		return self.retval


	def button_ok(self):
		self.retval = True
		QApplication.quit()


	def button_failed(self):
		QApplication.quit()

"""
	AutoCloseUrls will be evaluated on every response the embedded
	browser gets. If the path (with beginsWith) and the http status
	match, the browser will be closed to end the test.

	If result is set to false, the test will end as failed, instead
	as OK.
"""
class AutoCloseUrl(object):
	def __init__(self, path, status, result=True):
		self.path = path
		self.status = status
		self.result = result


class AutoCloseUrls(object):
	def __init__(self):
		self.urls = []

	def add(self, path, status, result):
		u = AutoCloseUrl(path,status,result)
		self.urls.append(u)

	def _url_is_equal(self, url, path, status):
		try:
			#python2
			if path.startsWith(url.path) and url.status == status:
				return True
		except AttributeError:
			#python3
			if path.startswith(url.path) and url.status == status:
				return True


		return False

	def check(self,path,status):
		for u in self.urls:
			print ("(%s ? %s + %s ? %s)" % ( u.path, path, u.status, status ))
			if self._url_is_equal(u, path, status):
				if u.result:
					return "OK"
				else:
					return "FAILED"
		return None
