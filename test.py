r"""
    Silo -- a simple, general purpose file system for LSL via HTTP
        version 2021-07-04
        Updated to improve test telmetry by John Dougan

        version 2006-07-09-beta
        by Zero Linden
        version 2021-08-22
        by John Dougan
    
        Copyright (c) 2006 Linden Lab
        Licensed under the "MIT" open source license.
        Changes Copyright (c) 2021 John Dougan
        Licensed under the "MIT" open source license.
    
    This file is only part of the whole distribution.
        test.py -- unit tests
    run by speciftying the root of the Silo as the sole argument
        python3 test.py http://silo.host.com/silopath > test.log

    There are behavior difference between web servers, these
    tests are biased for Apache.
    The built-in PHP Web Server handles some illegal path chars
    and then they just work.
"""

import os
import http.client
import sys
import time
import unittest
import urllib.parse

# Prints extra telemetry to stderr if True
SHOW_PATH = True

NeedsKey = False
#NeedsKey = True
    # if you change $firstPath in silo.php to be $keyPat
    # then change this to set NeedsKey to True

class SiloException (BaseException) :
    pass

class Silo:
    
    def __init__(self, url):
        self.baseURL = url
        # The parse defaut scheme maybe shoulf default to https in our modern crypto world
        parts = urllib.parse.urlparse(url, 'http', False)
        (self.baseScheme, self.baseHost, self.basePath) = parts[0:3]
    
    def goodStatus(self, status):
        return 200 <= status and status < 300
        
    def ensureGoodStatus(self, status, content):
        if not self.goodStatus(status):
            raise SiloException("unexpected http error status %d: %s " % (status, str(content)))
    
    def encode(self, body, encoding='utf-8'):
        headers = {}
        if body != None:
            body = str(body).encode(encoding)
            headers['Content-Type'] = 'text/plain;charset=' + encoding
        return (body, headers)
    
    def decode(self, rawContent, mimeType):
        if rawContent == None:
            return ''

        typeParts = mimeType.lower().split(';')
        if typeParts[0].strip().split('/')[0] != 'text':
            return ''

        charset = 'iso-8859-1'
        for param in typeParts[1:]:
            paramParts = param.lower().split('=', 1)
            if paramParts[0] == 'charset' and len(paramParts) == 2:
                charset = paramParts[1]

        return str(rawContent, charset)

    def rawConnect(self, verb, path, rawBody=None, reqheaders=None):
        # reqheaders can be None or a list of pairs
        if (self.baseScheme == 'https'):
            connection = http.client.HTTPSConnection(self.baseHost)
        else:
            connection = http.client.HTTPConnection(self.baseHost)
        if SHOW_PATH :
            print("", file=sys.stderr)
            print(verb,self.basePath + path, file=sys.stderr)
        if (rawBody == None):
            reqheadersdict ={}
        else:
            if False and ((reqheaders == None) or (len(reqheaders) == 0)) :
                raise SiloException("rawConnect: reqheaders empty, content-type at minimum:" , str(reqheaders) )
            else:
                print(reqheaders)
                reqheadersdict = dict(reqheaders)
        connection.request(verb, self.basePath + path, rawBody, reqheadersdict)
        response = connection.getresponse()
        status = response.status
        rawContent = response.read()
        respheaders = response.getheaders()
        mimeType = response.getheader(
                        'Content-Type', 'application/octet-stream')
            # according to RFC 2616, section 7.2.1, we are allowed to guess
            # the mime type in the absence of the Content-Type header
            # however, LSL takes a stricter view and will not guess text
        connection.close()
        return (status, rawContent, mimeType, respheaders)

    def connectHeaders(self, verb, path, body=None, encoding='utf-8', reqheaders=None):
        (rawBody, encheaders) = self.encode(body, encoding)
        if reqheaders == None :
            headers = encheaders.items()
        else:
            headers = reqheaders + list(encheaders.items())
        (status, rawContent, mimeType, respheaders ) = \
             self.rawConnect(verb, path, rawBody, headers)
        content = self.decode(rawContent, mimeType)
        return (status, content, respheaders)
    
    def connect(self, verb, path, body=None, encoding='utf-8', reqheaders=None):
        (status, content, respheaders) = \
            self.connectHeaders(verb, path, body=body, encoding=encoding, reqheaders=reqheaders)
        return (status, content)
    
    def get(self, path):
        (status, content) = self.connect("GET", path)
        self.ensureGoodStatus(status, content)
        return content
    
    def getheaders(self, path):
        (status, content, headers) = self.connectHeaders("GET", path)
        self.ensureGoodStatus(status, content)
        return (content, headers)

    def head(self, path):
        (status, content, headers) = self.connectHeaders("HEAD", path)
        self.ensureGoodStatus(status, content)
        return headers
    
    def put(self, path, body, encoding='utf-8', headers=None):
        (status, content) = self.connect("PUT", path, body, encoding, reqheaders=headers)
        self.ensureGoodStatus(status, content)
        return content
    
    def delete(self, path):
        (status, content) = self.connect("DELETE", path)
        self.ensureGoodStatus(status, content)
        return content
    
    def missing(self, path):
        (status, content) = self.connect("GET", path)
        if self.goodStatus(status):
            raise SiloException("unexpected (%d) status for %s: %s" \
                % (status, path, str(content)))

silo = None

class Tests_A_Setup(unittest.TestCase):
    def test000_baseURL(self):
        self.assertTrue(silo.baseScheme in ['http' , 'https'])
        self.assertTrue(silo.baseHost)
        self.assertTrue(silo.basePath)

        
class Tests_B_PathError(unittest.TestCase):
    def doPut(self, path, expectedOutcome):
        (status, content) = silo.connect("PUT", path, "data")
        if silo.goodStatus(status) != expectedOutcome:
            if expectedOutcome:
                expectedString = "good"
            else:
                expectedString = "bad"
            message = "expected %s status, got %d, processing path %s" % \
                (expectedString, status, path)
            if SHOW_PATH:
                print("doPut path ", path,file=sys.stderr)
                print("doPut content ", content,file=sys.stderr)
            self.fail(message)
    
    def doPutExpectGood(self, path):
        self.doPut(path, True)
    
    def doPutExpectBad(self, path):
        self.doPut(path, False)
        
    def test000_noPath(self):
        self.doPutExpectBad("")

    def test001_slashPath(self):
        self.doPutExpectBad("/")

    def test002_wordPath(self):
        self.doPut("/tuna-fish", not NeedsKey)

    def test003_badPath(self):
        self.doPutExpectBad("moo")

    def test004_dotPath(self):
        self.doPutExpectBad("/../../bin")

    def test005_hexPath(self):
        self.doPut("/E769FCEC3D1A4D538FC7BB3B0BBAFBEA", not NeedsKey)

    key = "/E769FCEC-3D1A-4D53-8FC7-BB3B0BBAFBEA"
    
    def test006_okayPath(self):
        self.doPutExpectGood(self.key + "/stuff")

    def test007_junkPath(self):
        self.doPutExpectBad(self.key + "/../foo")

    def test008_deepPath(self):
        self.doPutExpectBad(self.key + "/a/b/c/d/e/f/g/h/i/j/k")

    def test009_allowedCharacters(self):
        self.doPutExpectGood(self.key + "/0123456789")
        self.doPutExpectGood(self.key + "/ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.doPutExpectGood(self.key + "/abcdefghijklmnopqrstuvwxyz")
        
        allowedChars = "+-_"
        for c in allowedChars:
            self.doPutExpectGood(self.key + "/x" + c + "x")

        self.doPutExpectGood(self.key + "/%24x")
            # percent is only legal as an escape

    def _test010_disallowedCharacters(self):
        disallowedPathChars = ".~:@!$&'()*,;=#?"
            # legal as part of a URI path, query or fragment (see RFC 3986)
        disallowedOtherChars = "\"<>[\\]^`{|}"
            # not legal in URI path, query or fragment
            # should include space and del, but cause some versions of Apache
            # heartburn if you do
        for c in (disallowedPathChars + disallowedOtherChars):
            self.doPutExpectBad(self.key + "/x" + c + "x")

    # The next two sests are more about testing the remote web
    # server (apache vs php vs etc) So they have a lot of telemetry
    # so you can evaluate them for yourself. asserts are for apache.
    def test011_disallowedOtherCharacters(self):
        print("", file=sys.stderr)
        print("test011_disallowedOtherCharacters:", file=sys.stderr)
        disallowedOtherChars = "\"<>[\\]^`{|}"
            # not legal in URI path, query or fragment
            # should include space and del, but cause some versions of Apache
            # heartburn if you do
            # Current versions of Python filter for control chars
        good = []
        bad = []
        for c in (disallowedOtherChars):
            try:
                self.doPutExpectBad(self.key + "/x" + c + "x")
                if SHOW_PATH:
                    print("bad (pass)", file=sys.stderr)
                bad.append(c)
            except AssertionError as ex:
                good.append(c)
                if SHOW_PATH:
                    print("good (fail)", file=sys.stderr)
        print("failed (good response)", good, file=sys.stderr)
        print("succeeded (bad response)", bad, file=sys.stderr)
        self.assertTrue(len(good) == 0)
        print(":test011_disallowedOtherCharacters", file=sys.stderr)

    def test012_disallowedPathCharacters(self):
        print("", file=sys.stderr)
        print("test012_disallowedPathCharacters:", file=sys.stderr)
        disallowedPathChars = ".~:@!$&'()*,;=#?"
            # legal as part of a URI path, query or fragment (see RFC 3986)
        good = []
        bad = []
        for c in (disallowedPathChars):
            try:
                self.doPutExpectBad(self.key + "/x" + c + "x")
                if SHOW_PATH:
                    print("bad (pass)", file=sys.stderr)
                bad.append(c)
            except AssertionError as ex:
                good.append(c)
                if SHOW_PATH:
                    print("good (fail)", file=sys.stderr)
        print("failed (good response)", good, file=sys.stderr)
        print("succeeded (bad response)", bad, file=sys.stderr)
        self.assertTrue(len(good) == 0)
        print(":test012_disallowedPathCharacters", file=sys.stderr)


class Tests_C_Basic(unittest.TestCase):
    key = "/66ba1038-23b1-49f6-889d-00aa436a7e57"
    
    def setUp(self):
        silo.delete(self.key)
        silo.delete(self.key + "/")
         
    def test000_clear(self):
        silo.missing(self.key)
        silo.missing(self.key + "/")
        
    def test001_basic(self):
        where = self.key + "/simple"
        silo.missing(where)
        silo.put(where, "lalala")
        r = silo.get(where)
        self.assertEqual(r, "lalala")
        silo.delete(where)
        silo.missing(where)
        
    def test002_nestedData(self):
        above = self.key + "/nested/above"
        below = above + "/below"
        silo.put(above, "alpha");
        silo.put(below, "beta");
        self.assertEqual(silo.get(above), "alpha")
        self.assertEqual(silo.get(below), "beta")
        
    def test003_dirListing(self):
        silo.put(self.key + "/one", "uno")
        silo.put(self.key + "/two", "due")
        silo.put(self.key + "/three", "tre")
        r = silo.get(self.key + "/")
        self.assertEqual(r, "one\nthree\ntwo\n")
    
    def ensureWriteToFirstReadsFromSecond(self, keyA, keyB, delDir = False):
        silo.put(keyA, "insensitive")
        self.assertEqual(silo.get(keyB), "insensitive")
        
        delKey = keyB
        if delDir:
            delKey = keyB[:keyB.rfind('/')+1]
        silo.delete(delKey)
        silo.missing(keyA)
    
    def ensureKeysAreEquivalent(self, keyA, keyB, delDir = False):
        self.ensureWriteToFirstReadsFromSecond(keyA, keyB, delDir)
        self.ensureWriteToFirstReadsFromSecond(keyB, keyA, delDir)

    def test004_caseSensitivity(self):
        self.ensureKeysAreEquivalent(
            self.key.upper() + "/d",
            self.key.lower() + "/d",
            True)
            
        self.ensureKeysAreEquivalent(
            self.key.upper() + "/f",
            self.key.lower() + "/f",
            False)
    
    def test005_putStatus(self):
        k = self.key + "/new-node"
        (status, content) = silo.connect("PUT", k, "first time")
        self.assertEqual(status, 201)
        (status, content) = silo.connect("PUT", k, "second time")
        self.assertEqual(status, 200)
    

class Tests_D_RoundTrip(unittest.TestCase):
    # We check to see if the contyent-type and contents are
    # correctyly returned, which is a minimal test of the main
    # functions
    key = "/fa4b13c9-ed3c-462a-be6a-011c1bc464a9"
    
    def setUp(self):
        silo.delete(self.key)
        silo.delete(self.key + "/")
         
    def test000_clear(self):
        silo.missing(self.key)
        silo.missing(self.key + "/")
    
    def roundTrip(self, value, encoding="utf-8"):
        silo.put(self.key, value, encoding)
        givencontenttype =  'text/plain;charset=' + encoding
        #
        (content , headers) = silo.getheaders(self.key)
        contenttype = next(x[1] for x in headers if (x[0].lower() =='content-type') )
        self.assertEqual(contenttype, givencontenttype)
        self.assertEqual(content, value)
        #
        headheaders = silo.head(self.key)
        headcontenttype = next(x[1] for x in headheaders if (x[0].lower() =='content-type') )
        self.assertEqual(headcontenttype, givencontenttype)
    
    def roundTripXXX(self, value, encoding="utf-8"):
        silo.put(self.key, value, encoding)
        self.assertEqual(silo.get(self.key), value)
    
    def test001_simple(self):
        self.roundTrip("")
        self.roundTrip(" ")
        self.roundTrip("a")
        self.roundTrip("&<=>")

    def test002_asciiPrinting(self):
        self.roundTrip(' !"#$%&\'()*+,-./')
        self.roundTrip('0123456789:;<=>?')
        self.roundTrip('@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_')
        self.roundTrip('`abcdefghijklmnopqrstuvwxyz{|}~')

    def test003_encodingASCII(self):
        self.roundTrip("hello there", 'us-ascii')

    def test004_encodingISOLatin1(self):
        self.roundTrip('\u00C5ngstr\u00F6m', 'iso-8859-1')

    def test005_encodingUTF16(self):
        self.roundTrip('\u00C5ngstr\u00F6m \u03b2 \u2222', 'utf-16')

    def test006_encodingUTF16LE(self):
        self.roundTrip('\u00C5ngstr\u00F6m \u03b2 \u2222', 'utf-16le')

    def test007_encodingUTF16BE(self):
        self.roundTrip('\u00C5ngstr\u00F6m \u03b2 \u2222', 'utf-16be')


#class Tests_E_Headers:
class Tests_E_Headers(unittest.TestCase):
    key = "/b95a553f-fb65-4f0e-b1ca-c6e3f1bb93fc"
    
    def setUp(self):
        silo.delete(self.key)
        silo.delete(self.key + "/")
         
    def test000_clear(self):
        silo.missing(self.key)
        silo.missing(self.key + "/")
    
    def roundTrip(self, keyExt , value, encoding="utf-8", reqheaders=[]):
        fullKey = self.key + '/' + keyExt
        if False:
            print("", file=sys.stderr)
            print("putheaders", reqheaders, file=sys.stderr)
        silo.put(fullKey, value, encoding, headers=reqheaders)
        (content , respheaders) = silo.getheaders(fullKey)
        #
        # Add asserts here to verify stuff is being returned, once
        # the silo is cnfigured to do that
        # Turn the following on to eyeball the state
        if False:
            print("getheaders", respheaders, file=sys.stderr)
    
    def test001_noheaders(self):
        self.roundTrip('1a', "", reqheaders=[])
        self.roundTrip('1a', "", reqheaders=[])
        self.roundTrip('1b', " ", reqheaders=[])
        self.roundTrip('1c', "a", reqheaders=[])
        self.roundTrip('1d', "&<=>", reqheaders=[])

    def test002_simple(self):
        self.roundTrip('2a', "a", reqheaders=[('X-SecondLife-Note','Aa')])
        self.roundTrip('2b', "b", reqheaders=[('X-SecondLife-ApiLimit','Bb'), ('X-SecondLife-ApiLimit','Cc')])
        self.roundTrip('2c', "c", reqheaders=[('X-SecondLife-Note', 'Cc'), ('X-SecondLife-Note2', 'Ccc')] )
        self.roundTrip('2d', "d", reqheaders=[('X-ShouldNotWork', 'd')])


class Tests_Z_Timing(unittest.TestCase):
    key = '/55f62fac-b5ee-467a-9e3e-0e8cad0cd0de'
    
    def genKey(self):
        import uuid
        return "/" + str(uuid.uuid4())
    
    def readWriteKeys(self, keys):
        import random
        alphabet = "abcdefghijklmnopqrstuvwxyz0123456789-+.:"
        data = ''.join([ random.choice(alphabet) for i in range(100)])
        
        for k in keys:
            silo.put(k, data)
            self.assertEqual(silo.get(k), data)
    
    def deleteKeys(self, keys):
        for k in keys:
            silo.delete(k)
            
    def timingRuns(self, keyCount):
        (status, content) = silo.connect("GET", self.key)
        self.assertFalse(silo.goodStatus(status),
            "the silo's data tree isn't clear; try 'rm -rf data/*'")
        silo.put(self.key, "marker")
        
        keys = [ self.genKey() for i in range(keyCount)]
        for i in range(3):
            self.readWriteKeys(keys)
        self.deleteKeys(keys)

    def time10(self):
        self.timingRuns(10)
    
    def time100(self):
        self.timingRuns(100)
    
    def time1k(self):
        self.timingRuns(1000)
    
    def time10k(self):
        self.timingRuns(10000)
        

if __name__ == '__main__':
    if (len(sys.argv) <= 1):
      print("test.py: Expecting argument of a Silo root URL followed by optional unittest args")
      print(sys.argv)
      exit(1)
    silo = Silo(sys.argv[1])
    print("Silo Base URL: ", sys.argv[1], file=sys.stderr)
    del sys.argv[1]
    unittest.main()


