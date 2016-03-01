"""
Demo driver for the interactive browser test module.

test_target: The URL that will be queried. The response will then be given
to the interactive browser to proceed.

Limitations:
Handling http post is on the todo list

"""
#from future.standard_library import install_aliases
#install_aliases()

import urllib


from testharness_mod_interactivebrowser.module import ContentHandler, AutoCloseUrls

"""
fwclasses module holds proposals for new/modified framework classes
"""
import fwclasses


target_path =  "http://www.warwaris.at/brtest/"

if __name__ == "__main__":

	events = fwclasses.MyEvents()
	cookie_jar = fwclasses.MyCookieJar()

	request_url = target_path + "brtest.php"
	#request_url = "https://www.cacert.org/"

	"""
	Simulating some other content handler, which fails on a given request url ...
	"""

	urllib_request = urllib.request.Request(request_url)
	urllib_response = urllib.request.urlopen(urllib_request)
	cookie_jar.extract_cookies(urllib_response,urllib_request)

	handler_response = fwclasses.MyHandlerResponse('test-driver',
							fwclasses.MyHandlerResponse.FAILED_NEXT,
							cookie_jar = cookie_jar,
							urllib_request = urllib_request,
							urllib_response = urllib_response )

	events.store(fwclasses.EV_FAILED_HANDLER_RESPONSE, handler_response, sender='test-driver')

	print (events)

	"""
	... the framework now would see the failed return status, and either lookup the
	events to select the new request/response pair the next handler should work on,
	or simply just reuse that one, that failed.
	"""


	"""
	Preparing and calling the EB module.
	"""

	auto_close_urls = AutoCloseUrls()
	auto_close_urls.add(target_path + 'ack', 200, False)

	test = ContentHandler(None, None)
	result = test.handle_response(
				urllib_request,urllib_response,events, auto_close_urls, verify_ssl=True, cookie_jar=cookie_jar)


	print ( "Test result user action: " + result )

	#print (events.to_html())

	print (events)
