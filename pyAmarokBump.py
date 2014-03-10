# -*- coding: utf-8 -*-
import codecs, getopt, MySQLdb, os, random, math
import string, subprocess, sys, time, urllib
#import codecs, getopt, os, string, subprocess, sys, time
import xml.sax
import urllib
import unittest

#AMAROK_MUSIC_HOME = ["/home/pub/audio", "/home/pub/sound"]
AMAROK_MUSIC_HOME = ["/home"]

VERSION  = "0.0.6"
DEBUG_FLAG = "false"
PRETEND_FLAG = "false"
UNITTEST_FLAG = "false"
SCRIPT_NAME = "pyAmarokBump-" + VERSION + ".py"

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
  toBeBumped = []
  
  for item in names:
    fullFilePath = os.path.abspath(os.getcwd())
    fullFilePath = os.path.join(fullFilePath, dirname)
    fullFilePath = os.path.join(fullFilePath, item)
    
    if os.path.isfile(fullFilePath):
      #result = findHelper(dirname, item, fullFilePath, bump)    
      for audioType in [".mp3", ".flac", ".ogg", ".m4a", ".mp4"]:
        fileExtension = os.path.splitext( fullFilePath )
        if fileExtension[1].lower() == audioType:
          debug("\n\rFound " + audioType + " in " + dirname + ": " + item)
          foundAudioFiles = "true"
          toBeBumped.append(fullFilePath)

       
  if foundAudioFiles == "false":
    debug("No audiofiles found in directory: " + dirname)
  else:
    bumpAmarokStats(bump[0], toBeBumped, bump[1])
  return

#######################################################################
#
# For the given (Amarok) database connection, increase the playcount by
# the given bump number
#
def findHelper(dirname, item, fullFilePath, bump):
  foundAudioFiles = "false"
  toBeBumped = []
  for audioType in [".mp3", ".flac", ".ogg", ".m4a", ".mp4"]:
    fileExtension = os.path.splitext( fullFilePath )
    if fileExtension[1].lower() == audioType:
      debug("\n\rFound " + audioType + " in " + dirname + ": " + item)
      foundAudioFiles = "true"
      toBeBumped.append(fullFilePath)
  
  bumpAmarokStats(bump[0], toBeBumped, bump[1])
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
# Class for tweaking Amarok statistics
#
class BumpAmarokStatistics:
  #######################################################################
  #
  # Update the statistics table
  #
  # For the given (Amarok) database connection, increase the playcount by
  # the given bump number
  #
  def bumpAudioPlaycount(self, dbConnection, fullFilePath, bump):
    debug("\n\ractual bump method")
    cursor = dbConnection.cursor()
    try:
      
      AllPossiblePaths = AMAROK_MUSIC_HOME
      
      #
      # Initially I wanted to use the RAND() SQL function, but that resulted in warnings that
      #
      # "Statement may not be safe to log in statement format."
      #
      # Looking at the documentation (http://dev.mysql.com/doc/refman/5.1/en/replication-rbr-safe-unsafe.html)
      # The culprit is the RAND() method
      # 
      #
      #newUpdateStatement = """UPDATE statistics LEFT JOIN urls ON statistics.url = urls.id """
      #newUpdateStatement += """ SET score=LEAST(100, FLOOR(RAND() * 10) + 1 + score), """
      #newUpdateStatement += """ playcount=playcount+""" + str(bump) + ""","""
      #newUpdateStatement += """ rating=LEAST(10, rating+FLOOR(RAND()*6/5)) """
      #newUpdateStatement += """ WHERE urls.rpath IN ( """

      scoreBump = random.randint(0, 10)
      ratingBump = int (random.random() *6/5)
      newUpdateStatement = """UPDATE statistics LEFT JOIN urls ON statistics.url = urls.id """
      newUpdateStatement += """ SET score=LEAST(100, """ + str(scoreBump) + """ + 1 + score), """
      newUpdateStatement += """ playcount=playcount+""" + str(bump) + ""","""
      newUpdateStatement += """ rating=LEAST(10, rating+""" + str(ratingBump) + """) """
      newUpdateStatement += """ WHERE urls.rpath IN ("""
            
      for singleFile in fullFilePath:
        debug ("in loop")
        singleFile = singleFile.replace("\"", "\\\"")
        singleFile = singleFile.replace(AMAROK_MUSIC_HOME[0], ".")
        debug (singleFile)
        newUpdateStatement += """ '""" + singleFile.replace("'","\\'") + """', """
      
      #Remove last two characters (i.e. ' and the whitespace)  
      newUpdateStatement = newUpdateStatement[:-2]
      newUpdateStatement += """);"""
      
      debug(newUpdateStatement)
      
      self.executeUpdateStatement(cursor, newUpdateStatement)
      result = cursor.rowcount
      debug("Results of Update: " + str(result))
      
      if (len(fullFilePath) != result):
        warning("Mismatch of playcount update row count versus input.")
        warning("|".join(fullFilePath) + "|")
          
    except Exception as detail:
      warning(str(detail))
      debug("Error while updating record for : " + "|".join(fullFilePath) + "|")
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
    #print(message)
    print message

def bumpAmarokStats(connection, fileOrDirectory, playCountBump):
  bump = BumpAmarokStatistics()
  #debug("fileOrDirectory = " + fileOrDirectory)
  amarokFilePath = fileOrDirectory
  bump.bumpAudioPlaycount(connection, amarokFilePath, playCountBump)


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
  print "WARNING : " + message

#######################################################################
#
# Print Usage Information
#
def usage():
  #print("")
  #print("Usage information")
  #print("")
  #print("To increase the playcount of a file or group of files on disk, ")
  #print("execute the following:")
  #print("")
  #print("\t" + SCRIPT_NAME + " --playcount-bump=<number> [Path to File(s)]")
  #print("")
  print ""
  print "Usage information"
  print ""
  print "To increase the playcount of a file or group of files on disk, "
  print "execute the following:"
  print ""
  print "\t" + SCRIPT_NAME + " --playcount-bump=<number> [Path to File(s)]"
  print ""
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
                 ["help", "debug", "pretend", "playcount-bump=", "unittest"])
  except getopt.GetoptError as err:
    # print help information and exit:
    warning(str(err))
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
  elif len(args) == 0:
    warning("Missing command-line arguments")
    usage()
  elif playCountBump < 1:
    warning("A positive playcount bump number must be specified")
    usage()
  else:
    debug("\n\rConnecting to database")
    connection = connectToDatabase("localhost", "amarok_toy", "amarokuser", "amarokpasswd")
    #connection = connectToDatabase("localhost", "amarok24", "amarok24", "fri-(cab)")
    
    try:
      bumpInfo =  [connection, playCountBump]
      
      # for python wrapper
      for cmdInput in args:
        fileOrDirectory = string.lstrip(cmdInput, "\"")
        fileOrDirectory = string.rstrip(fileOrDirectory, "\"")
          
        # Need full path for deciding if this is a file or a directory
        if os.path.isdir(fileOrDirectory):
          os.path.walk(fileOrDirectory, find, bumpInfo)
        else:
          #elif os.path.isfile(fileOrDirectory):
          bumpAmarokStats(connection, [fileOrDirectory], playCountBump)
        #else:
        #  warning(fileOrDirectory + " is neither a directory nor a file.")
    finally:
      debug("Closing connection to database")
      connection.close()

if __name__ == "__main__":
    main()
