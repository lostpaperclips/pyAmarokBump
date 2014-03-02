# -*- coding: utf-8 -*-
import codecs, getopt, MySQLdb, os, random
import string, subprocess, sys, time, urllib
#import codecs, getopt, os, string, subprocess, sys, time
import xml.sax
import urllib
import unittest

ITUNES_MUSIC_HOME_PREFIXES = ["file://localhost/Z:/Music", "file://localhost/C:/Users/Christopher Crammond/Music/iTunes/iTunes Music"]
AMAROK_MUSIC_HOME = "/home/pub/audio"

VERSION  = "0.0.2"
DEBUG_FLAG = "false"
ITUNES_FLAG = "false"
PRETEND_FLAG = "false"
UNITTEST_FLAG = "false"
SCRIPT_NAME = "pyAmBump-" + VERSION + ".py"

#######################################################################
#
# args: extention to find
# dirname: name of current directory
# list of files in the current directory
#
def find(bump, dirname, names):
  debug("\n\rEntering find()");
  debug("  bump = " + str(bump));
  debug("  dirname = " + dirname);
  debug("  names = " + str(names))
  foundAudioFiles = "false"
  for item in names:
    fullFilePath = os.path.abspath(os.getcwd())
    fullFilePath = os.path.join(fullFilePath, dirname)
    fullFilePath = os.path.join(fullFilePath, item)
    
    if os.path.isfile(fullFilePath):
      result = findHelper(dirname, item, fullFilePath, bump)
      if result == "true":
        foundAudioFiles = "true"
       
  if foundAudioFiles == "false":
    debug("No audiofiles found in directory: " + dirname)
  return

#######################################################################
#
# For the given (Amarok) database connection, increase the playcount by
# the given bump number
#
def findHelper(dirname, item, fullFilePath, bump):
  foundAudioFiles = "false"
  for audioType in [".mp3", ".flac", ".ogg", ".m4a"]:
    fileExtension = os.path.splitext( fullFilePath )
    if fileExtension[1].lower() == audioType:
      debug("\n\rFound " + audioType + " in " + dirname + ": " + item)
      foundAudioFiles = "true"
      bumpAmarokStats(bump[0], fullFilePath, bump[1])
  return foundAudioFiles

#######################################################################
# 
# Unit Test Suite
#
class UnitTestFunctions(unittest.TestCase):
  
  def setUp(self):
    self.sut = BumpAmarokStatistics()

  def test_generateNewScore_All_Zeroes(self):
    self.assertEquals(0, self.sut.generateNewScore(0,0,0))

  def test_generateNewScore_All_ZeroesWithNegativePlaycount(self):
    self.assertEquals(0, self.sut.generateNewScore(-1,0,0))

  def test_generateNewScore_50_Previous100(self):
    self.assertEquals(50, self.sut.generateNewScore(0,100,0))
    
  def test_generateNewScore_NotBelowZeroOrAboveHundred(self):
    for playcount in range (0, 121):
      for prevscore in range (0 ,101, 5):
        for percentage in range (0 ,101, 5):
          score = self.sut.generateNewScore(playcount,prevscore,percentage)
          message = "playcount = {0}, prevscore = {1}, percentage = {2}".format(playcount,prevscore,percentage)
          self.assertTrue(0 <= score, message)
          self.assertTrue(score <= 100, message)

#######################################################################
# 
# Class for importing an iTunes 9.x Library
#
class iTunesLibraryContentXmlParser(xml.sax.handler.ContentHandler):
  
  FOUND_INTEGER = "false"
  FOUND_KEY = "false"
  FOUND_LOCATION = "false"
  FOUND_PLAYCOUNT = "false"
  FOUND_STRING = "false"
  itunesLocation = ""
  itunesPlayCount = 0
  
  def __init__(self):
    self.FOUND_INTEGER = "false"
    self.FOUND_KEY = "false"
    self.FOUND_LOCATION = "false"
    self.FOUND_PLAYCOUNT = "false"
    self.FOUND_STRING = "false"
  
  def characters(self, content):
    if self.FOUND_LOCATION == "true":
      self.itunesLocation = content
      self.FOUND_LOCATION = "false"
    elif self.FOUND_PLAYCOUNT == "true":
      self.itunesPlayCount = int(content)
      self.FOUND_PLAYCOUNT= "false"
    elif content == "Location":
      self.FOUND_LOCATION = "true" 
    elif content == "Play Count":
      self.FOUND_PLAYCOUNT= "true" 
  
  #######################################################################
  #
  # Prints debugging messages (if the debugging flag has been set)
  #
  def debug(self, message):
    if DEBUG_FLAG == "true":
      print(message)
  
  def endDocument(self):
    debug("End of the iTunes Library XML document")
    
  def endElement(self, name):
    if name == "dict":
      if self.itunesLocation != "" and self.itunesPlayCount > 0:    
        self.updateStatistics()
        self.itunesLocation = ""
        self.itunesPlayCount = 0
      FOUND_INTEGER = "false"
      FOUND_KEY = "false"
      FOUND_LOCATION = "false"
      FOUND_PLAYCOUNT = "false"
      FOUND_STRING = "false"

  def startDocument(self):
    debug("Beginning of the iTunes Library XML document")
    
  def startElement(self, name, attrs):
    if name == "dict":
      FOUND_INTEGER = "false"
      FOUND_KEY = "false"
      FOUND_LOCATION = "false"
      FOUND_PLAYCOUNT = "false"
      FOUND_STRING = "false"     
    if name == "key":
      FOUND_KEY = "true"

  def updateStatistics(self):
    filename = self.itunesLocation
    
    filename = self.updateStatisticsHelper(filename)
    
    filename = filename.replace("%2500", "%")
    filename = filename.replace("%0025", "%")
    #filename = filename.replace("%250022", "\"")
    #filename = filename.replace("%25002A", "*")
    #filename = filename.replace("%25002B", "\"")
    #filename = filename.replace("%25003A", ":")
    #filename = filename.replace("%25003F", "?")
    #filename = filename.replace("%2500252", "%2")
    #filename = filename.replace("%2500252F", "%2F")
    filename = filename.replace("%0022", "\"")
    filename = filename.replace("%002A", "*")
    filename = filename.replace("%0025", "%")
    filename = filename.replace("%003A", ":")
    filename = filename.replace("%003F", "?")    
    
    for stripper in ITUNES_MUSIC_HOME_PREFIXES:
      filename = filename.replace(stripper, "")

    filename = filename.replace('\\', '/')
    filename = AMAROK_MUSIC_HOME + filename
    #debug("tranformed pathname: " + filename)
    if os.path.isfile(filename):
      #warning("Unable to locate file: \r\n" + filename)
      print(filename + "|"+str(self.itunesPlayCount))

  #######################################################################
  #
  #
  def updateStatisticsHelper(self, filename):
    filename = filename.replace("%20", " ")
    filename = filename.replace("%21", "!")
    filename = filename.replace("%22", "\"")
    filename = filename.replace("%23", "#")
    filename = filename.replace("%24", "$")
    filename = filename.replace("%25", "%")

    filename = filename.replace("%26", "&")
    filename = filename.replace("%27", "'")
    filename = filename.replace("%28", "(")
    filename = filename.replace("%29", ")")
    filename = filename.replace("%2A", "*")
    filename = filename.replace("%2B", "+")
    filename = filename.replace("%2C", ",")
    filename = filename.replace("%2D", "-")
    filename = filename.replace("%2E", ".")
    filename = filename.replace("%2F", "/")

    filename = filename.replace("%3A", ":")
    filename = filename.replace("%3B", ";")
    filename = filename.replace("%3C", "<")
    filename = filename.replace("%3D", "=")
    filename = filename.replace("%3E", ">")
    filename = filename.replace("%3F", "?")
    filename = filename.replace("%40", "@")
    
    
    filename = filename.replace("%5B", "[")
    filename = filename.replace("%5D", "]")
    filename = filename.replace("%5F", "_")
    
    filename = filename.replace("%80", "€")
    filename = filename.replace("%82", "‚")
    filename = filename.replace("%83", "ƒ")
    filename = filename.replace("%84", "„")
    filename = filename.replace("%85", "…")
    filename = filename.replace("%86", "†")
    filename = filename.replace("%87", "‡")
    filename = filename.replace("%88", "ˆ")
    filename = filename.replace("%89", "‰")
    filename = filename.replace("%8A", "Š")
    filename = filename.replace("%8B", "‹")
    filename = filename.replace("%8C", "Œ")
    filename = filename.replace("%8E", "Ž")
    filename = filename.replace("%91", "‘")
    filename = filename.replace("%92", "’")
    filename = filename.replace("%93", "“")
    filename = filename.replace("%94", "”")
    filename = filename.replace("%95", "•")
    filename = filename.replace("%96", "–")
    filename = filename.replace("%97", "—")
    filename = filename.replace("%98", "˜")
    filename = filename.replace("%99", "™")
    filename = filename.replace("%9A", "š")
    filename = filename.replace("%9B", "›")
    filename = filename.replace("%9C", "œ")
    filename = filename.replace("%9E", "ž")
    filename = filename.replace("%9F", "Ÿ")
    
    filename = filename.replace("%A1", "¡")
    filename = filename.replace("%A2", "¢")
    filename = filename.replace("%A3", "£")
    filename = filename.replace("%A4", "¤")
    filename = filename.replace("%A5", "¥")
    filename = filename.replace("%A6", "¦")
    filename = filename.replace("%A7", "§")
    filename = filename.replace("%A8", "¨")
    filename = filename.replace("%A9", "©")
    filename = filename.replace("%AA", "ª")
    filename = filename.replace("%AB", "«")
    filename = filename.replace("%AC", "¬")
    filename = filename.replace("%AE", "®")
    filename = filename.replace("%AF", "¯")
    filename = filename.replace("%B0", "°")
    filename = filename.replace("%B1", "±")
    filename = filename.replace("%B2", "²")
    filename = filename.replace("%B3", "³")
    filename = filename.replace("%B4", "´")
    filename = filename.replace("%B5", "µ")
    filename = filename.replace("%B6", "¶")
    filename = filename.replace("%B7", "·")
    filename = filename.replace("%B8", "¸")
    filename = filename.replace("%B9", "¹")
    filename = filename.replace("%BA", "º")
    filename = filename.replace("%BB", "»")
    filename = filename.replace("%BC", "¼")
    filename = filename.replace("%BD", "½")
    filename = filename.replace("%BE", "¾")
    filename = filename.replace("%BF", "¿")
    
    filename = filename.replace("%C0", "À")
    filename = filename.replace("%C1", "Á")
    filename = filename.replace("%C2", "Â")
    filename = filename.replace("%C3", "Ã")
    filename = filename.replace("%C4", "Ä")
    filename = filename.replace("%C5", "Å")
    filename = filename.replace("%C6", "Æ")
    filename = filename.replace("%C7", "Ç")
    filename = filename.replace("%C8", "È")
    filename = filename.replace("%C9", "É")
    filename = filename.replace("%CA", "Ê")
    filename = filename.replace("%CB", "Ë")
    filename = filename.replace("%CC", "Ì")
    filename = filename.replace("%CD", "Í")
    filename = filename.replace("%CE", "Î")
    filename = filename.replace("%CF", "Ï")
    filename = filename.replace("%D0", "Ð")
    filename = filename.replace("%D1", "Ñ")
    filename = filename.replace("%D2", "Ò")
    filename = filename.replace("%D3", "Ó")
    filename = filename.replace("%D4", "Ô")
    filename = filename.replace("%D5", "Õ")
    filename = filename.replace("%D6", "Ö")
    filename = filename.replace("%D7", "×")
    filename = filename.replace("%D8", "Ø")
    filename = filename.replace("%D9", "Ù")
    filename = filename.replace("%DA", "Ú")
    filename = filename.replace("%DB", "Û")
    filename = filename.replace("%DC", "Ü")
    
    filename = filename.replace("%E0", "à")
    filename = filename.replace("%E1", "á")
    filename = filename.replace("%E2", "â")
    filename = filename.replace("%E3", "ã")
    filename = filename.replace("%E4", "ä")
    filename = filename.replace("%E5", "å")
    filename = filename.replace("%E6", "æ")
    filename = filename.replace("%E7", "ç")
    filename = filename.replace("%E8", "è")
    filename = filename.replace("%E9", "é")
    filename = filename.replace("%EA", "ê")
    filename = filename.replace("%EB", "ë")
    filename = filename.replace("%EC", "ì")
    filename = filename.replace("%ED", "í")
    filename = filename.replace("%EE", "î")
    filename = filename.replace("%EF", "ï")
    filename = filename.replace("%F0", "ð")
    filename = filename.replace("%F1", "ñ")
    filename = filename.replace("%F2", "ò")
    filename = filename.replace("%F3", "ó")
    filename = filename.replace("%F4", "ô")
    filename = filename.replace("%F5", "õ")
    filename = filename.replace("%F6", "ö")
    filename = filename.replace("%F7", "÷")
    filename = filename.replace("%F8", "ø")
    filename = filename.replace("%F9", "ù")
    filename = filename.replace("%FA", "ú")
    filename = filename.replace("%FB", "û")
    filename = filename.replace("%FC", "ü")
    
    return filename

#######################################################################
# 
# Class for tweaking Amarok statistics
#
class BumpAmarokStatistics:
  #######################################################################
  #
  # Update the statistics_permanent
  #
  # For the given (Amarok) database connection, increase the playcount by
  # the given bump number
  #
  def bumpAudioPlaycount_statistics_permenent(self, dbConnection, fullFilePath, bump):
    debug("\n\ra) find id from the url/path")
    fullFilePathAsUrl = string.replace(fullFilePath, " ", "%20")
      
    cursor = dbConnection.cursor()
    try:
      findUrlIdStatement = """
      SELECT statistics_permanent.playcount FROM statistics_permanent WHERE 
      statistics_permanent.url = "file://""" + fullFilePathAsUrl + """";"""
      self.executeSelectStatement(cursor, findUrlIdStatement)
      createAndAccessDate = time.strftime("%Y-%m-%d %H:%M:%S")
      
      if cursor.rowcount == 0:
        debug("\n\rc - i) create playcount record")   
        debug("Inserted play count will be " + str(int(bump)))
        insertPlaycountStatement = """INSERT INTO statistics_permanent (url,firstplayed,lastplayed,score,playcount) VALUES("file://""" + \
                fullFilePathAsUrl + """", \"""" + createAndAccessDate + """\", \"""" + createAndAccessDate + \
                """\", 0, """ + str(bump)  + """);""" 
        findPlayCountResult = self.executeInsertStatement(cursor, insertPlaycountStatement)
      else: #if cursor.rowcount >= 1:
        debug("\n\rc - ii) update/add current playcount")   
        findUrlIdResult =  cursor.fetchall()
        dbPlaycount = str(findUrlIdResult[0][0])   
        debug("Current playcount is " + dbPlaycount)
        debug("Updated play count will be " + str(int(dbPlaycount) + int(bump)))
        updatePlaycountStatement = """UPDATE statistics_permanent SET statistics_permanent.playcount = statistics_permanent.playcount + """ \
                + str(bump) 
        updatePlaycountStatement = updatePlaycountStatement + """, statistics_permanent.lastplayed = \"""" \
                + createAndAccessDate + "\""
        updatePlaycountStatement = updatePlaycountStatement + """ WHERE statistics_permanent.url = "file://""" \
                + fullFilePathAsUrl + """";"""
        findPlayCountResult = self.executeUpdateStatement(cursor, updatePlaycountStatement)
    except Exception as detail:
      warning(str(detail))
      debug("Error while updating record for : " + fullFilePath)
    finally:
      debug("Closing the cursor")
      cursor.close()
    return
    
  #######################################################################
  #
  # Update the statistics table
  #
  # For the given (Amarok) database connection, increase the playcount by
  # the given bump number
  #
  def bumpAudioPlaycount(self, dbConnection, fullFilePath, bump):
    debug("\n\ra) find id from the url/path")
    fullFilePath = fullFilePath.replace("\"", "\\\"")
    cursor = dbConnection.cursor()
    try:
      findUrlIdStatement = """
      SELECT id FROM urls WHERE 
      urls.rpath = ".""" + fullFilePath + """";"""
      self.executeSelectStatement(cursor, findUrlIdStatement)
      debug("curor.rowcount : " + str(cursor.rowcount))
      createAndAccessDate = str(int(time.time()))
      
      if cursor.rowcount != 1:
        warning("No entry in url table for " + fullFilePath)
      else:
        debug("\n\rb) update/add current playcount")
        findUrlIdResult =  cursor.fetchall()
        urlId = str(findUrlIdResult[0][0])   
        
        # find the appropriate entry in the statistics table and updatePlaycountStatement
        findStatisticsPlaycountStatement = """SELECT score,rating,playcount FROM statistics WHERE statistics.url = """ + urlId + """;"""
        self.executeSelectStatement(cursor, findStatisticsPlaycountStatement)
        
        if cursor.rowcount == 0:
          debug("\n\rc - i) create playcount record")   
          debug("Inserted play count will be " + str(int(bump)))
          
          newrating = random.randint(7, 10)
          newscore = self.generateNewScore(bump, random.randint(50, 100), newrating * 10)
          
          insertPlaycountStatement = """INSERT INTO statistics (url,createdate,accessdate,score,rating,playcount) VALUES(""" + \
                urlId + """, """ + createAndAccessDate + """, """ + createAndAccessDate + \
                """, """ + str(newscore) + """, """ + str(newrating) +""", """ + str(bump)  + """);""" 
          self.executeInsertStatement(cursor, insertPlaycountStatement)
        else:
          debug("\n\rc - ii) update/add current playcount")
          findPlaycountResult =  cursor.fetchall()
          
          dbScore = findPlaycountResult[0][0]
          if dbScore is None:
	    dbScore = random.randint(50, 100)
          dbRating = findPlaycountResult[0][1]
          dbPlayCount = findPlaycountResult[0][2]
          
          debug("Current playcount is " + str(dbPlayCount))
          debug("Updated play count will be " + str(int(dbPlayCount) + int(bump)))
          newscore = self.generateNewScore(int(dbPlayCount) + int(bump), int(dbScore), int(dbRating)*10)
          newrating = random.randint(int(dbRating), 10)
          updatePlaycountStatement = """UPDATE statistics SET statistics.playcount = statistics.playcount + """ \
                + str(bump) 
          updatePlaycountStatement = updatePlaycountStatement + """, statistics.accessdate = """ \
                + createAndAccessDate
          updatePlaycountStatement = updatePlaycountStatement + """, statistics.score = """ \
                + str(newscore)
          updatePlaycountStatement = updatePlaycountStatement + """, statistics.rating = """ \
                + str(newrating)
          updatePlaycountStatement = updatePlaycountStatement + """ WHERE statistics.url = """ \
                + urlId + """;"""
          findPlayCountResult = self.executeUpdateStatement(cursor, updatePlaycountStatement)
    except Exception as detail:
      warning(str(detail))
      debug("Error while updating record for : " + fullFilePath)
    finally:
      debug("Closing the cursor")
      cursor.close()
    return
  
  #######################################################################
  #
  # Run a SQL INSERT statement
  #
  def executeInsertStatement(self, cursor, statement):
    debug("Running INSERT = '" + statement +"'")
    if PRETEND_FLAG == 'false':
      cursor.execute (statement)
      debug("Executed INSERT = '" + statement +"'")
    debug("Number of rows found from INSERT: " + str(cursor.rowcount))
    return
  
  #######################################################################
  #
  # Run a SQL SELECT statement
  #
  def executeSelectStatement(self, cursor, statement):
    debug("Running SELECT = '" + statement +"'") 
    cursor.execute (statement)
    debug("Executed SELECT = '" + statement +"'") 
    debug("Number of rows found from SELECT: " + str(cursor.rowcount))
    return
  
  #######################################################################
  #
  # Run a SQL UPDATE statement
  #
  def executeUpdateStatement(self, cursor, statement):
    debug("Running UPDATE = '" + statement +"'")
    if PRETEND_FLAG == 'false':
      cursor.execute (statement)
      debug("Executed UPDATE = '" + statement +"'")
    debug("Number of rows found from UPDATE: " + str(cursor.rowcount)) 
  
  #######################################################################
  #
  # For the given (Amarok) database connection, increase the playcount by
  # the given bump number
  #
  # Base logic taken from http://amarok.kde.org/wiki/FAQ
  #
  def generateNewScore(self, playcount, prevscore, percentage):
    newscore = 0
    if( playcount <= 0 ): # not supposed to be less, but what the hell.
      newscore = ( prevscore + percentage ) / 2
    else:
      newscore = ( ( prevscore * playcount ) + percentage ) / ( playcount + 1 )    
    return newscore

#######################################################################
#
# Establish a connection to the Amarok database
#
def connectToDatabase(machineName, databaseName, username, password):
  debug("\n\rEntering connectToDatabase()")
  debug("  hostname= " + machineName)
  debug("  databaseName = " + databaseName)
  debug("  username = " + username)
  debug("  password = <Ssssh>")
  return MySQLdb.connect (host = machineName,
                           user = username,
                           passwd = password,
                           db = databaseName) 

#######################################################################
#
# Prints debugging messages (if the debugging flag has been set)
#
def debug(message):
  if DEBUG_FLAG == "true":
    print(message)

def bumpAmarokStats(connection, fileOrDirectory, playCountBump):
  bump = BumpAmarokStatistics()
  bump.bumpAudioPlaycount(connection, fileOrDirectory, playCountBump)

#######################################################################
#
# Parses exported iTunes XML Library
#
def importItunesLibary(pathToItunesLibaryXml):
  warning("implement this method: importItunesLibary")
  try:
    #f = open(pathToItunesLibaryXml, 'r')
    f = codecs.open(pathToItunesLibaryXml, encoding='utf-8')
    inSource = xml.sax.xmlreader.InputSource()
    inSource.setEncoding('utf-8')
    inSource.setByteStream(f) 
    
    iContentHandler = iTunesLibraryContentXmlParser()
    
    iParser = xml.sax.make_parser()
    iParser.setContentHandler(iContentHandler)
    #iParser.parse(inSource)
    
    for line in f:
      tmpLine = line
      #tmpLine  = tmpLine.replace("&#38;","&amp;")
      tmpLine  = tmpLine.replace("&#38;","%26")
      #filename = filename.replace("%5B", "[")
      iParser.feed(tmpLine)
  finally:
    f.close()

#######################################################################
#
# Run Unit Test Suite
#
def runUnitTests():
  suite = unittest.TestLoader().loadTestsFromTestCase(UnitTestFunctions)
  unittest.TextTestRunner(verbosity=2).run(suite)

#######################################################################
#
# Prints warning messages to STDERR
#
def warning(message):
  #print("WARNING : " + message, file=sys.stderr)
  print >> sys.stderr, "WARNING : " + message

#######################################################################
#
# Print Usage Information
#
def usage():
  print("")
  print("Usage information")
  print("")
  print("To increase the playcount of a file or group of files on disk, ")
  print("execute the following:")
  print("")
  print("\t" + SCRIPT_NAME + " --playcount-bump=<number> [Path to File(s)]")
  print("")
  print("To increase the playcount from an exported iTunes Libary, ")
  print("execute the following:")
  print("")
  print("\t" + SCRIPT_NAME + " --itunes=<Path to iTunesLibary.xml>")
  print("")

#######################################################################
#
# Start of the 'main()' function
# 
def main():
  #######################################################################
  #
  # Read Command-Line
  #
  global SCRIPT_NAME
  SCRIPT_NAME = sys.argv[0]
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hdp", \
                 ["help", "debug", "itunes=", "pretend", "playcount-bump=", "unittest"])
  except (getopt.GetoptError, err) as e:
    # print help information and exit:
    warning(err)
    usage()
    sys.exit(2)
  #######################################################################
  #
  # Parse Command-Line Options and Arguments
  # 
  pathToItunesLibaryXml = ""
  playCountBump = 0
  for o, a in opts:
    if o in ("-h", "--help"):
      usage()
      sys.exit()
    elif o in ("-d", "--debug"):
      global DEBUG_FLAG
      DEBUG_FLAG = "true"
    elif o in ("--itunes"):
      global ITUNES_FLAG
      ITUNES_FLAG = "true"
      pathToItunesLibaryXml = a
    elif o in ("-p", "--pretend"):
      global PRETEND_FLAG
      PRETEND_FLAG = "true"
    elif o == "--playcount-bump":
      playCountBump = a
    elif o == "--unittest":
      global UNITTEST_FLAG
      UNITTEST_FLAG = "true"
    else:
      assert False, "unhandled option"
    
  #######################################################################
  #
  # Sanity checks 
  #
  debug(str(args))
  if UNITTEST_FLAG == "true":
    runUnitTests()
  elif len(args) == 0 and ITUNES_FLAG == "false":
    warning("Missing command-line arguments")
    usage()
  elif playCountBump < 1 and ITUNES_FLAG == "false":
    warning("A positive playcount bump number must be specified")
    usage()
  else:
    debug("\n\rConnecting to database")
    #connection = connectToDatabase("localhost", "amarok_toy", "amarokuser", "amarokpasswd")
    connection = connectToDatabase("localhost", "amarok24", "amarok24", "fri-(cab)")
    
    try:
      bumpInfo =  [connection, playCountBump]
      if ITUNES_FLAG == "true":
        importItunesLibary(pathToItunesLibaryXml)
      else:
        # for bash wrapper
        #os.path.walk(string.join(args), find, bumpInfo)
        #return

        # for python wrapper
        for cmdInput in args:
          fileOrDirectory = string.lstrip(cmdInput, "\"")
          fileOrDirectory = string.rstrip(fileOrDirectory, "\"")
          if os.path.isdir(fileOrDirectory):
            os.path.walk(fileOrDirectory, find, bumpInfo)
          else:
            #elif os.path.isfile(fileOrDirectory):
            bumpAmarokStats(connection, fileOrDirectory, playCountBump)
          #else:
          #  warning(fileOrDirectory + " is neither a directory nor a file.")
    finally:
      debug("Closing connection to database")
      connection.close()

if __name__ == "__main__":
    main()
