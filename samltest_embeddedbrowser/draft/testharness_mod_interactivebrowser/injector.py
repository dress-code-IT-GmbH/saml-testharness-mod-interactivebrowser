from PyQt4.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkCookie, QNetworkCookieJar, QNetworkReply
from PyQt4.QtCore import QUrl

try:
    from PyQt4.QtCore import QString
except ImportError:
    # we are using Python3 so QString is not defined
    QString = type("")

from PyQt4.QtCore import   QTextStream,  QVariant, QTimer, SIGNAL
from PyQt4 import QtCore

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

	def __init__(self, original_request_url):
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
	def __init__(self, parent, url, content, operation):
		QNetworkReply.__init__(self, parent)
		self.content = content
		self.offset = 0

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
	The InjectedQNetworkAccessManager will create a InjectedNetworkReply if
	the Request is an InjectedQNetworkRequest to prefill the browser with
	html data. It will be transparent to normal QNetworkRequests
"""
class InjectedQNetworkAccessManager(QNetworkAccessManager):
	autocloseOk = QtCore.pyqtSignal()
	autocloseFailed = QtCore.pyqtSignal()

	def __init__(self, parent = None):
		super(InjectedQNetworkAccessManager, self).__init__(parent)

	def setInjectedResponse(self, response):
		self.response = response

	def _getCookieHeader(self):
		info = self.response
		header = info.getheader('Set-Cookie')
		if header:
			return 'Set-Cookie: ' + header
		else:
			return None

	def _createCookieJarfromInjectedResponse(self, default_domain):
		#ugly, but works around bugs in parseCookies
		cookies = []

		cj = QNetworkCookieJar()

		cookie_header = self._getCookieHeader()
		if not cookie_header:
			return cj

		#print (cookie_header)

		tmp_cookieList = QNetworkCookie.parseCookies(cookie_header)

		#print (tmp_cookieList)

		if not tmp_cookieList:
			return cj

		for tmp_cookie in tmp_cookieList:
			if not tmp_cookie.domain():
				tmp_cookie.setDomain(QString(default_domain))

			cookies.append( tmp_cookie )

		cookies = cookies + tmp_cookieList

		cj.setAllCookies(cookies)
		return cj

	def _cookie_default_domain(self,request):
		url = request.url()
		return url.host()


	def createRequest(self, op, request, device = None):

		if InjectedQNetworkRequest.thatRequestHasMagicQt4(request):
			r =  InjectedNetworkReply(self, request.url(), self.response.read(), op)

			default_cookie_domain = self._cookie_default_domain(request)
			cookiejar = self._createCookieJarfromInjectedResponse(default_cookie_domain)
			self.setCookieJar(cookiejar)

		else:
			r = QNetworkAccessManager.createRequest(self, op, request, device)

		r.finished.connect(self.checkAutoCloseUrls)

		return r

	def setAutoCloseUrls(self,autocloseurls):
		self.autocloseurls = autocloseurls


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
		if result == 'FAILED':
			self.autocloseFailed.emit()


