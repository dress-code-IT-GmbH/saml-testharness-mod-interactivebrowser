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

from aatest import contenthandler

class HandlerResponse(object):
	def __init__(self, content_processed, user_action='',
				cookie_jar=None, http_response=None, response=None):
		self.content_processed = content_processed
		self.user_action = user_action
		self.cookie_jar = cookie_jar
		self.http_response = http_response
		self.response = response		

"""

	TestAction displays the resonse from urllib and takes over the
	handling in an embedded browser.

	__init__ takes an AutoCloseUrls object, which can hold URLs and
	http status codes, to automagically stop the process returning a
	defined result.

	run takes the response object from urllib2 and the corresponding
	url for that response.

"""

class ContentHandler(contenthandler.ContentHandler):
	def __init__(self, interactions, conv=None):
		contenthandler.ContentHandler.__init__(self)
		"""
			this content handler does not support automatic interactions
			we make sure it is not set ..
		"""
		if interactions:
			raise NotImplementedError
		
		self.conv = conv
		self.cjar = {}
		self.features = {}
		self.handler = None
		self.auto_close_urls = []
		self.http_request = None
		self.http_response = None
		
		self.last_response = None
		
	def handle_response(self, http_response, auto_close_urls, http_request, 
					conv=None, verify_ssl=True, cookie_jar=None):
		if cookie_jar:
			# TODO
			raise NotImplementedError
	
		if http_response is None:
			return
		
		self.http_response = http_response
		self.auto_close_urls = auto_close_urls
		self.http_request = http_request
		self.conv = conv
		self.verify_ssl = verify_ssl
		
		return self._run()

	def _run(self):
		self.retval = 'NOK'


		request = InjectedQNetworkRequest(self.http_request)

		nam = InjectedQNetworkAccessManager(ignore_ssl_errors=True)
		nam.setInjectedResponse(self.http_response, self.http_request)
		nam.setAutoCloseUrls(self.auto_close_urls)

		nam.autocloseOk.connect(self.button_ok)
		nam.autocloseFailed.connect(self.button_failed)

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

		test_abort_button = QPushButton("Abort Test")
		test_abort_button.clicked.connect(self.button_abort)

		url_input = UrlInput(browser)

		grid.addWidget(test_ok_button, 1, 0)
		grid.addWidget(test_failed_button, 1, 1)
		grid.addWidget(test_abort_button, 1, 2)
		grid.addWidget(url_input, 2, 0, 1, 3)
		grid.addWidget(browser, 4, 0, 1, 3)

		main_frame = QWidget()
		main_frame.setLayout(grid)
		main_frame.show()

		app.exec_()
		
		processed = False
		if self.retval == 'OK' or self.retval == 'NOK':
			processed = True
		
		handler_response = HandlerResponse(processed, user_action=self.retval)
		
		return handler_response


	def button_ok(self):
		self.retval = 'OK'
		QApplication.quit()


	def button_failed(self):
		self.retval = 'NOK'
		QApplication.quit()
		
	def button_abort(self):
		self.retval = 'aborted'
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
			#print ("check (%s ? %s + %s ? %s)" % ( u.path, path, u.status, status ))
			if self._url_is_equal(u, path, status):
				if u.result:
					return "OK"
				else:
					return "NOK"
		return None
