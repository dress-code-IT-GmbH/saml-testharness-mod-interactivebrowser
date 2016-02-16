"""
	Proposals for framework addons.
	
	This classes are meant as blueprints for the expansion of framework
	classes.	
"""

from future.standard_library import install_aliases
import time

"""
	My CookieJar
	
		Extending the httplib CookieJar to return a http header line,
		which allows for further conversion of cookies, relevant to
		a request.
"""
from http.cookiejar import CookieJar

#import pprint
class MyCookieJar(CookieJar):
	
	def __init__(self, policy=None):
		CookieJar.__init__(self,policy)


	"""
	http header attributes. Note that the http.cookiejar lib
	must construct the headers out of the jar for a given request.
	"""

	def http_header_attrs(self,urllib_request):
		self._cookies_lock.acquire()
		attrs = None
		try:
			self._policy._now = self._now = int(time.time())
			cookies = self._cookies_for_request(urllib_request)
			
			attrs = self._cookie_attrs(cookies)		
	
		finally:
			self._cookies_lock.release()

		self.clear_expired_cookies()
		return attrs

	
"""
	My HandlerResponse 
		
		Renamed http_request into urllib_request to make urllib compatibility visible
		Renamed content_processed into processing_status and defined some stati, which
		should maybe declared elswhere?
		AFAIG urllib_* should be mandatory, then response should not be neccessary?
		Do we need the cookie_jar here? The cookies relevant for the request can be restored
		from urllib_request and response
"""
from aatest import contenthandler

class MyHandlerResponse(contenthandler.HandlerResponse):
	PROCESSED = 0
	FAILED_NEXT = 1
	FAILED_FINAL = 2
	
	def __init__(self, content_handler_name, processing_status, outside_html_action=None,
				 tester_error_description=None,
				 cookie_jar=None, urllib_request=None, urllib_response=None, response=None):
		
		"""
			:content_handler_name: the name of the content handler. This is used by the Conversation
			object, to determine the responses, which belong to one (or in general, the last)
			content handler.
			:urllib_request: the request in urllib compatible form.
			:urllib_response:  the response in urllib compatible form.
		"""
		
		
		self.urllib_request = urllib_request
		self.urllib_response = urllib_response
		self.content_handler_name = content_handler_name
		self.processing_status = processing_status
		
		content_processed = False
		if processing_status == MyHandlerResponse:
			content_processed = True
		
		super(MyHandlerResponse, self).__init__(content_processed, outside_html_action,
				 tester_error_description,
				 cookie_jar, urllib_response, response)
	

	def response_content_type(self):
		"""
			will return the native content type header, which could include other informations
			like character set coding. Test on substrings.
		"""
		if not self.urllib_response:
			return None
		
		info = self.urllib_response.info()
		content_type = info.getheader('Content-Type')
		return content_type

	def response_content_type_is(self,search_string):
		content_type_string = self.response_content_type()
		if search_string in content_type_string:
			return True
		return False

	def processing_status_is(self,status):
		if self.processing_status == status:
			return True
		return False

	def cookie_jar(self):
		"""
			if needed, the cookie jar could be restored here from request+response
		"""
		raise NotImplementedError

"""
	I feel i haven't dug enough into the usage of Conversation to modify it, so this is just the
	blueprint of the added functionality, exposed to test handlers.
	
	To make replacement easier, this "conversation" is named conv_log throughout the code
"""
class ConvLog(object):
	def __init__(self):
		self.response_log = []
		
	def log_response(self, handler_response ):
		self.response_log.append(handler_response)

	def last_content_handler_name(self):
		
		try:
			last_handler_response = self.response_log[-1]
		except KeyError:
			return NULL
		name = last_handler_response.content_handler_name	
		return name
		
	def last_failed_next_handler_responses(self, content_type):
		"""
			Will return a [] of MyHandlerResponse Objects from the log, filtered by:
			- it is from the last handler operation
			- it is marked as FAILED_NEXT
			- it has the content_type given
		"""	
		last_content_handler_name = self.last_content_handler_name()
	
		filtered_responses = []
		
		if not last_content_handler_name:
			return filtered_responses 
	
	
		for handler_response in reversed(self.response_log):
			this_content_handler_name = handler_response.content_handler_name
			if this_content_handler_name != last_content_handler_name:
				break
			if handler_response.processing_status_is(MyHandlerResponse.FAILED_NEXT):
				if handler_response.response_content_type_is(content_type):
					filtered_responses.append(handler_response)
		
		return filtered_responses 
		
		
		