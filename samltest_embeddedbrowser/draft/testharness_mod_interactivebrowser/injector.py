#from future.standard_library import install_aliases

from PyQt4.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkCookie, QNetworkCookieJar, QNetworkReply
from PyQt4.QtCore import QUrl

try:
	# Python2
	import StringIO
	from PyQt4.QtCore import QString
	from urllib import addinfourl
except ImportError:
	# Python3
	QString = type("")
	from io import StringIO
	from io import BytesIO
	from urllib.response import addinfourl

from PyQt4.QtCore import   QTextStream,  QVariant, QTimer, SIGNAL, QByteArray
from PyQt4 import QtCore

from http.cookiejar import CookieJar
#import mimetools

#install_aliases()

from urllib.request import Request as UrllibRequest
from urllib.response import addinfourl
import email

from fwclasses import MyHandlerResponse

import pprint
"""
	The pyqt bindings don't care much about our classes, so we have to
	use some trickery to get around that limitations. And there are some
	nasty bugs too:

	InjectedQNetworkRequest adds a magic parameter to the URl, which is
	then used to detect that the QNetworkRequest we get, should have been
	the injected one.

	Having InjectedQNetworkRequest knowing its response (cookies) would
	be the logical way, but because that info is getting lost, we have to
	take care about that in InjectedQNetworkAccessManager. Sucks.

	There is a bug in the binding (no QList) that prevents us from having
	cookie handling in the QNetworkReply, so it's also done on the wrong
	place.

	Most of that will be fixed in the future of PyQt.

	Things named with Qt4 are known to break in Qt5.
"""



"""
	InjectedQNetworkRequest is the Request that will not be sent to the
	network, but written into the embedded browser.
"""
class InjectedQNetworkRequest(QNetworkRequest):
	magic_query_key = QString('magic_injected')
	magic_query_val = QString('4711')

	def __init__(self, original_urllib_request):
		original_request_url = original_urllib_request.get_full_url()
		new_url =self.putMagicIntoThatUrlQt4(QUrl(original_request_url))
		super(InjectedQNetworkRequest, self).__init__(new_url)

	def putMagicIntoThatUrlQt4(self,url):
		new_url = url
		new_url.setQueryItems([(self.magic_query_key,self.magic_query_val)])
		return new_url

	@classmethod
	def thatRequestHasMagicQt4(self,request):
		url = request.url()
		value = url.queryItemValue(self.magic_query_key)
		if value == self.magic_query_val:
			return True
		return False


"""
	The InjectedNetworkReply will be given to the browser.
"""
class InjectedNetworkReply(QNetworkReply):
	def __init__(self, parent, url, content, operation, urllib_request, urllib_response):
		QNetworkReply.__init__(self, parent)
		self.content = content
		self.offset = 0

		self.urllib_request = urllib_request
		self.urllib_response = urllib_response

		self.setHeader(QNetworkRequest.ContentTypeHeader, "text/html")
		self.setHeader(QNetworkRequest.ContentLengthHeader, len(self.content))

		QTimer.singleShot(0, self, SIGNAL("readyRead()"))
		QTimer.singleShot(0, self, SIGNAL("finished()"))
		self.open(self.ReadOnly | self.Unbuffered)
		self.setUrl(QUrl(url))

	def abort(self):
		pass

	def bytesAvailable(self):
		# NOTE:
		# This works for Win:
		#	  return len(self.content) - self.offset
		# but it does not work under OS X.
		# Solution which works for OS X and Win:
		#	 return len(self.content) - self.offset + QNetworkReply.bytesAvailable(self)
		return len(self.content) - self.offset + QNetworkReply.bytesAvailable(self)

	def isSequential(self):
		return True

	def readData(self, maxSize):
		if self.offset < len(self.content):
			end = min(self.offset + maxSize, len(self.content))
			data = self.content[self.offset:end]
			self.offset = end
			return data


"""
	The SniffingNetworkReply stores the content.
	TODO: As this is using up twice the mem for the response: make this just store the
	interesting stuff, up to a configurable amount, and just passing thru the rest.
"""

class SniffingNetworkReply(QNetworkReply):
	def __init__(self, parent, request, reply, operation):
		#self.sniffed_data = ""
		#self.sniffed_data = QByteArray()

		QNetworkReply.__init__(self, parent)
		self.open(self.ReadOnly | self.Unbuffered)
		self.setUrl(QUrl(request.url()))
		self.setRequest(request)
		self.offset = 0

		reply.finished.connect(self.onReplyFinished)

	def abort(self):
		pass

	def bytesAvailable(self):
		c_bytes = len(self.sniffed_data) - self.offset + QNetworkReply.bytesAvailable(self)
		return c_bytes

	def isSequential(self):
		return True

	def readData(self, maxSize):
		if self.offset < len(self.sniffed_data):
			end = min(self.offset + maxSize, len(self.sniffed_data))
			data = self.sniffed_data[self.offset:end]
			self.offset = end
			return data

	def onReplyFinished(self):
		self.reply = self.sender()


		raw_header_pairs = self.reply.rawHeaderPairs()
		for header in raw_header_pairs:
			self.setRawHeader(header[0],header[1])

		http_status = self.reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
		self.setAttribute(QNetworkRequest.HttpStatusCodeAttribute, http_status)

		bytes_available = self.reply.bytesAvailable()
		self.sniffed_data = self.reply.read(bytes_available + 512)

		self.readyRead.emit()
		self.finished.emit()

"""
	The InjectedQNetworkAccessManager will create a InjectedNetworkReply if
	the Request is an InjectedQNetworkRequest to prefill the browser with
	html data. It will be transparent to normal QNetworkRequests
"""
class InjectedQNetworkAccessManager(QNetworkAccessManager):
	autocloseOk = QtCore.pyqtSignal()
	autocloseFailed = QtCore.pyqtSignal()

	requestFinishing = QtCore.pyqtSignal()

	def __init__(self, parent = None, ignore_ssl_errors=False):
		super(InjectedQNetworkAccessManager, self).__init__(parent)
		self.ignore_ssl_errors = ignore_ssl_errors
		self.urllib_request = None
		self.urllib_response = None
		self.http_cookie_jar = None

	def setInjectedResponse(self, urllib_request, urllib_response, http_cookie_jar):
		self.urllib_request = urllib_request
		self.urllib_response = urllib_response
		self.http_cookie_jar = http_cookie_jar

	def _cookie_default_domain(self,request):
		url = request.url()
		return url.host()

	def _import_cookie_jar(self,http_cookie_jar,default_domain):

		cj = QNetworkCookieJar()
		cookie_attrs = http_cookie_jar.http_header_attrs(self.urllib_request)
		cookies = self._parse_cookie_attribs_into_QtCookies_list(cookie_attrs, default_domain)
		cj.setAllCookies(cookies)
		return cj

	def _parse_cookie_attribs_into_QtCookies_list(self, cookie_attrs, default_domain):
		#ugly, but works around bugs in parseCookies
		cookies = []

		for cookie_attr in cookie_attrs:
			# parsing every attribute on its own because parser seems to be <censored>!
			tmp_cookie_list = QNetworkCookie.parseCookies(cookie_attr)
			if tmp_cookie_list:
				tmp_cookie = tmp_cookie_list[0]
				if not tmp_cookie.domain():
					tmp_cookie.setDomain(QString(default_domain))
				cookies.append(tmp_cookie)

		return cookies


	def createRequest(self, op, request, device = None):
		if InjectedQNetworkRequest.thatRequestHasMagicQt4(request):
			r =  InjectedNetworkReply(self, request.url(), self.urllib_response.read(), op, self.urllib_request, self.urllib_response)
			default_cookie_domain = self._cookie_default_domain(request)
			cookiejar = self._import_cookie_jar(self.http_cookie_jar, default_cookie_domain)
			self.setCookieJar(cookiejar)
		else:
			self.urllib_response = None
			self.urllib_request = None
			original_r = QNetworkAccessManager.createRequest(self, op, request, device)
			original_r.sslErrors.connect(self.sslErrorHandler)
			r = SniffingNetworkReply(self, request, original_r, op)

		r.finished.connect(self.requestFinishedActions)

		return r

	def sslErrorHandler(self,errorlist):
		response = self.sender()
		if self.ignore_ssl_errors:
			response.ignoreSslErrors(errorlist)
		else:
			print ("Test aborted because of ssl errors:")
			for error in errorlist:
				print ( error.errorString() )
			self.autocloseFailed.emit()

	def setAutoCloseUrls(self,autocloseurls):
		self.autocloseurls = autocloseurls

	def _create_urllib_data(self, qt_network_reply):
		qt_network_request = qt_network_reply.request()

		request_url = qt_network_request.url()
		request_headers = {}
		for header_name in qt_network_request.rawHeaderList():
			header = qt_network_request.rawHeader(header_name)
			request_headers.update({header_name.data():header.data()})

		url = request_url.toEncoded().data()
		self.urllib_request = UrllibRequest(url, headers=request_headers)

		#py2: output_file = StringIO.StringIO()
		output_file = StringIO()
		raw_header_pairs = qt_network_reply.rawHeaderPairs()
		headers = []
		for header in raw_header_pairs:
			hd_string = '%s: %s' % (header[0], header[1])
			output_file.write(hd_string)
			headers.append(hd_string)
		output_file.write("\n")
		output_file.write(str(qt_network_reply.sniffed_data))

		headers_mstr = email.message_from_string('\n'.join(headers))

		origurl = qt_network_reply.url().toEncoded().data()

		self.urllib_response = addinfourl(output_file, headers_mstr, origurl)


	def requestFinishedActions(self):
		qt_network_reply = self.sender()

		try:
			self.urllib_request = qt_network_reply.urllib_request
			self.urllib_response = qt_network_reply.urllib_response
		except AttributeError:
			self._create_urllib_data(qt_network_reply)

		self.requestFinishing.emit()
		self.checkAutoCloseUrls()



	def checkAutoCloseUrls(self):
		sender = self.sender()
		url = sender.url().toString()
		http_status_pre = sender.attribute( QNetworkRequest.HttpStatusCodeAttribute)
		try:
			#python2
			http_status = http_status_pre.toInt()
			http_status_result = http_status[0]
		except AttributeError:
			#python 3
			http_status_result = http_status_pre

		result = self.autocloseurls.check(url, http_status_result)
		if result == 'OK':
			self.autocloseOk.emit()
		if result == 'NOK':
			self.autocloseFailed.emit()

