import sys
from PyQt4.QtGui import QApplication,  QGridLayout, QWidget, QPushButton
from PyQt4.QtWebKit import QWebView
try:
	from PyQt4.QtCore import QString
except ImportError:
	# we are using Python3 so QString is not defined
	QString = type("")

from fwclasses import MyCookieJar
import fwclasses
import aatest.events

from .injector import InjectedQNetworkRequest, InjectedQNetworkAccessManager
from .gui import UrlInput

import time

from aatest import contenthandler
import pprint

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

		self.cookie_jar = fwclasses.MyCookieJar()

	def handle_response(self, urllib_request, urllib_response, events, auto_close_urls, verify_ssl=True, cookie_jar=None):

		if cookie_jar:
			self.cookie_jar = cookie_jar

		if not urllib_request:
			raise Exception('Parameter error: urllib_request is not set')
		if not urllib_response:
			raise Exception('Parameter error: urllib_response is not set')

		self.auto_close_urls = auto_close_urls
		self.events = events
		self.verify_ssl = verify_ssl
		self.start_urllib_request = urllib_request
		self.start_urllib_response = urllib_response

		return self._run()

	def _run(self):
		self.retval = 'NOK'

		self.handler_response_cache = []

		injected_qt_request = InjectedQNetworkRequest(self.start_urllib_request)

		self.nam = InjectedQNetworkAccessManager(ignore_ssl_errors=True)
		self.nam.setInjectedResponse(
			self.start_urllib_request,
			self.start_urllib_response,
			self.cookie_jar
			)
		self.nam.setAutoCloseUrls(self.auto_close_urls)

		self.nam.autocloseOk.connect(self.autoclose_ok)
		self.nam.autocloseFailed.connect(self.autoclose_failed)

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

		processed = False
		if self.retval == 'OK' or self.retval == 'NOK':
			processed = True

		return self.retval

	def _update_handler_results(self):
		""" This is called on every finished request-response in the browser """
		self._update_cookie_jar()
		self._event_log_cache_results()

	def _update_cookie_jar(self):

		self.cookie_jar.extract_cookies(
				self.nam.urllib_response,
				self.nam.urllib_request
				)

	def _event_log_cache_results(self):

		timestamp = time.time()
		cache_element = {
						'urllib_response': self.nam.urllib_response,
						'urllib_request': self.nam.urllib_request,
						'cookie_jar': self.cookie_jar,
						'time': timestamp,
						}

		self.handler_response_cache.append(cache_element)

	def _write_event_log_cache(self, status, all_but_last_ok=False):

		first_pop = True
		while self.handler_response_cache:
			event = self.handler_response_cache.pop()
			this_status = status
			if all_but_last_ok and not first_pop:
				this_status = aatest.events.EV_HANDLER_RESPONSE

			hr_status = fwclasses.MyHandlerResponse.PROCESSED
			if this_status == fwclasses.EV_FAILED_HANDLER_RESPONSE:
				hr_status = fwclasses.MyHandlerResponse.FAILED_NEXT


			handler_response = fwclasses.MyHandlerResponse(
							'embeddedbrowser',
							hr_status,
							cookie_jar = event['cookie_jar'],
							urllib_request = event['urllib_request'],
							urllib_response = event['urllib_response']
							)
			# we use the somewhat "private" append, because we need to store data with the
			# original event time
			ev = aatest.events.Event(event['time'], this_status, handler_response,
						 '', '','embeddedbrowser' )
			self.events.events.append(ev)

			first_pop = False

	def autoclose_ok(self):
		self.retval = 'OK'
		self._write_event_log_cache(aatest.events.EV_HANDLER_RESPONSE)
		QApplication.quit()


	def autoclose_failed(self):
		self.retval = 'NOK'
		self._write_event_log_cache(fwclasses.EV_FAILED_HANDLER_RESPONSE, all_but_last_ok=True)
		QApplication.quit()

	def button_ok(self):
		self.retval = 'OK'
		self._write_event_log_cache(aatest.events.EV_HANDLER_RESPONSE)
		QApplication.quit()


	def button_failed(self):
		self.retval = 'NOK'
		self._write_event_log_cache(fwclasses.EV_FAILED_HANDLER_RESPONSE)
		QApplication.quit()

	def button_abort(self):
		self.retval = 'aborted'
		self._write_event_log_cache(fwclasses.EV_FAILED_HANDLER_RESPONSE)
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
