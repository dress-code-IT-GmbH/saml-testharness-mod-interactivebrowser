import sys
from PyQt4.QtGui import QApplication,  QGridLayout, QWidget, QPushButton
from PyQt4.QtWebKit import QWebView
try:
	from PyQt4.QtCore import QString
except ImportError:
	# we are using Python3 so QString is not defined
	QString = type("")

from fwclasses import MyCookieJar


from .injector import InjectedQNetworkRequest, InjectedQNetworkAccessManager
from .gui import UrlInput

from aatest import contenthandler
import pprint

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
	def __init__(self, interactions, conv_log):
		contenthandler.ContentHandler.__init__(self)
		"""
			this content handler does not support automatic interactions
			we make sure it is not set ..
		"""
		if interactions:
			raise NotImplementedError

		self.conv_log = conv_log
		self.cjar = {}
		self.features = {}
		self.handler = None
		self.auto_close_urls = []
		self.http_request = None
		self.http_response = None

		self.last_response = None

		self.cookie_jar = MyCookieJar()

	def handle_response(self, conv_log, auto_close_urls, verify_ssl=True, cookie_jar=None):

		if cookie_jar:
			self.cookie_jar = cookie_jar

		self.auto_close_urls = auto_close_urls
		self.conv_log = conv_log
		self.verify_ssl = verify_ssl

		return self._run()


	def _select_handler_response(self):
		responses = self.conv_log.last_failed_next_handler_responses('text/html')
		if responses:
			return responses[0]
		else:
			return None

	def _run(self):
		self.retval = 'NOK'

		self.handler_response_cache = []

		self.selected_handler_response = self._select_handler_response()
		if not self.selected_handler_response:
			return None

		injected_qt_request = InjectedQNetworkRequest(self.selected_handler_response.urllib_request)

		self.nam = InjectedQNetworkAccessManager(ignore_ssl_errors=True)
		self.nam.setInjectedResponse(
			self.selected_handler_response.urllib_request,
			self.selected_handler_response.urllib_response,
			self.cookie_jar
			)
		self.nam.setAutoCloseUrls(self.auto_close_urls)

		self.nam.autocloseOk.connect(self.button_ok)
		self.nam.autocloseFailed.connect(self.button_failed)

		self.nam.requestFinishing.connect(self._update_handler_results)

		app = QApplication([])
		grid = QGridLayout()
		browser = QWebView()

		page = browser.page()
		page.setNetworkAccessManager(self.nam)

		browser.load(injected_qt_request, self.nam.GetOperation)



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

		#pprint.pprint (self.cookie_jar._cookies)

		processed = False
		if self.retval == 'OK' or self.retval == 'NOK':
			processed = True

		handler_response = HandlerResponse(processed, user_action=self.retval)

		return handler_response

	def _update_handler_results(self):

		print ("update cookies!")

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
