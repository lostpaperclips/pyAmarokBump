# -*- coding: utf-8 -*-
import codecs, getopt, MySQLdb, os, random, math
import collections
import string, subprocess, sys, time, urllib
import xml.sax
import urllib
import unittest

#AMAROK_MUSIC_HOME = ["/home/pub/audio", "/home/pub/sound"]
AMAROK_MUSIC_HOME = ["/home"]

VERSION  = "0.0.8"
BATCH_FLAG = "false"
DEBUG_FLAG = "false"
PRETEND_FLAG = "false"
UNITTEST_FLAG = "false"
FUNCTIONAL_TEST_FLAG = "false"
SCRIPT_NAME = "pyAmarokBump-" + VERSION + ".py"

#######################################################################
#
# args: extention to find
# dirname: name of current directory
# list of files in the current directory
#
def findv2(bump, dirname, names):
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
    
    if os.path.isdir(fullFilePath):
      toBeBumped = findv2(bump, fullFilePath, os.listdir(fullFilePath))
    elif os.path.isfile(fullFilePath):
      for audioType in [".mp3", ".flac", ".ogg", ".m4a", ".mp4"]:
        fileExtension = os.path.splitext( fullFilePath )
        if fileExtension[1].lower() == audioType:
          debug("\n\rFound " + audioType + " in " + dirname + ": " + item)
          foundAudioFiles = "true"
          toBeBumped.append(fullFilePath)
       
  if foundAudioFiles == "false":
    debug("No audiofiles found in directory: " + dirname)
  return toBeBumped



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
  
  return foundAudioFiles

def findDuplicates(fileList):
    return [x for x, y in collections.Counter(fileList).items() if y > 1]

def findUnique(fileList):
    seen = set()
    seen_add = seen.add
    return [ x for x in fileList if x not in seen and not seen_add(x)]

#######################################################################
# 
# Functional Test Suite
#
# Theses tests are run against a well-known database, refer to the 
# functional-test folder for a script to create the database as well
# as 
#
class FunctionalTestFunctions(unittest.TestCase):
  
  def setUp(self):
    self.sut = BumpAmarokStatistics()
    
    try:
      readDefaultFile = os.path.abspath(os.getcwd())
      readDefaultFile = os.path.join(readDefaultFile, "functional-tests")
      readDefaultFile = os.path.join(readDefaultFile, "mysql.pyAmarokBump.functional.cnf")
      refreshDatabase = os.path.abspath(os.getcwd())
      refreshDatabase = os.path.join(refreshDatabase, "functional-tests")
      refreshDatabase = os.path.join(refreshDatabase, "amarok_contents.sql")
      #debug("Reading the file to (re-)populate the database: %s" % refreshDatabase )
      #with open(refreshDatabase,'r') as inserts:
      #    for statement in inserts:
      #        print statement
      #        cursor.execute(statement)
      from subprocess import Popen, PIPE
      process = Popen('mysql --defaults-file=%s' % (readDefaultFile),
                      stdout=PIPE, stdin=PIPE, shell=True)
      output = process.communicate('source ' + refreshDatabase)[0]
      self.connection = MySQLdb.connect(read_default_file=readDefaultFile)

    except MySQLdb.Error, e:
        try:
            self.fail( "MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
        except IndexError:
            self.fail( "MySQL Error: %s" % str(e))
  
  def tearDown(self):
      if None != self.connection:
          debug("closing database")
          self.connection.close
      else:
           debug("no database connection alive")

  def test_functional(self):
      # 1) check that the expected default value is X
      # 2) update by a
      # 3) check that the expected default value is X + a
      #self.sut.executeSelectStatement(cursor, statement):
      cursor = self.connection.cursor()
      
      # Build a select statement like:
      # SELECT * 
      # FROM statistics 
      # LEFT JOIN urls 
      # ON urls.id = statistics.url 
      # WHERE urls.rpath = './pub/audio/BigDaddyKane/28Bars/Big Daddy Kane - 28 Bars Of Kane.mp3';
      
      selectStatement = "SELECT statistics.playcount FROM statistics "
      selectStatement += "JOIN urls ON urls.id = statistics.url WHERE urls.rpath = '%s'";
      selectStatement = selectStatement % "./pub/audio/BigDaddyKane/28Bars/Big Daddy Kane - 28 Bars Of Kane.mp3"
      initialResults = self.sut.executeSelectStatement(cursor, selectStatement)
      findPlaycountResult =  cursor.fetchall()
      #cursor.close()
      dbPlayCount = findPlaycountResult[0][0]
      self.assertEquals(4, dbPlayCount, "Pre-bump playcount of %s does not match" % dbPlayCount)
      
      updateFileList = []
      updateFileList.append("./pub/audio/BigDaddyKane/28Bars/Big Daddy Kane - 28 Bars Of Kane.mp3")
      updateFileList.append("./pub/audio/BigDaddyKane/28Bars/Big Daddy Kane - 28 Bars Of Kane.mp3")
      batchBumpAmarokStats(self.connection, updateFileList, 3, "XXX")
      
      cursor2 = self.connection.cursor()
      secondResults = self.sut.executeSelectStatement(cursor2, selectStatement)
      findPlaycountResult =  cursor2.fetchall()
      cursor2.close()
      dbPlayCount = findPlaycountResult[0][0]
      self.assertEquals(4+2*3, dbPlayCount, "Post-bump playcount of %s does not match" % dbPlayCount)

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

  def test_batchInput_fileRead(self):
      fileList = []
      fileList.append("/home/pub/audio/madlib/Quasimoto - Yessir/|2")
      fileList.append("/home/pub/audio/FourTet/EarlyUnreleased/ | 1 ")
      fileList.append("/home/pub/audio/NumeroGroup/1514 Oliver Avenue (Basement)/|4")
      fileList.append("/home/pub/audio/Jimi Hendrix/Jimi Hendrix - Are You Experienced/ | 1")
      fileList.append("/home/pub/audio/Jimi Hendrix/Jimi Hendrix - Are You Experienced/")
      fileList.append("/home/pub/audio/BlackMekon/StolenBible2/")
      fileList.append(" /home/pub/audio/BlackOpera/MaskDayMegamix/ | 6 ")
      
      answer = self.sut.optimizeBatch(fileList)
      
      self.assertEquals(self.sut.convertListToString(answer[1]), "/home/pub/audio/BlackMekon/StolenBible2/ /home/pub/audio/FourTet/EarlyUnreleased/")
      self.assertEquals(self.sut.convertListToString(answer[2]), "/home/pub/audio/Jimi Hendrix/Jimi Hendrix - Are You Experienced/ /home/pub/audio/madlib/Quasimoto - Yessir/")
      self.assertEquals(self.sut.convertListToString(answer[4]), "/home/pub/audio/NumeroGroup/1514 Oliver Avenue (Basement)/")
      self.assertEquals(self.sut.convertListToString(answer[6]), "/home/pub/audio/BlackOpera/MaskDayMegamix/")

  def test_batch_Reduce_All_Unique(self):
      fileList = ["a", "b", "c", "e", "d"]
      answer = self.sut.optimizeListOfFiles(fileList)
      unique = answer[0]
      dups = answer[1]
      self.assertEquals(len(unique), 5, "wrong size of unique elements")
      self.assertEquals(len(dups), 0, "wrong size of duplicate elements")
      self.assertEquals(unique[0], "a", "wrong unique element at index 0: " + unique[0] )
      self.assertEquals(unique[1], "b", "wrong unique element at index 1: " + unique[1] )
      self.assertEquals(unique[2], "c", "wrong unique element at index 2: " + unique[2] )
      self.assertEquals(unique[3], "d", "wrong unique element at index 3: " + unique[3] )
      self.assertEquals(unique[4], "e", "wrong unique element at index 4: " + unique[4] )

  def test_batch_Reduce_All_Duplicates(self):
      fileList = ["a", "a", "b", "a", "b"]
      answer = self.sut.optimizeListOfFiles(fileList)
      unique = answer[0]
      dups = answer[1]
      self.assertEquals(len(unique), 0, "wrong size of unique elements")
      self.assertEquals(len(dups), 5, "wrong size of duplicate elements")
      self.assertEquals(dups[0], "a", "wrong dups element at index 0: " + dups[0] )
      self.assertEquals(dups[1], "a", "wrong dups element at index 1: " + dups[1] )
      self.assertEquals(dups[2], "a", "wrong dups element at index 2: " + dups[2] )
      self.assertEquals(dups[3], "b", "wrong dups element at index 3: " + dups[3] )
      self.assertEquals(dups[4], "b", "wrong dups element at index 4: " + dups[4] )
  
  def test_batch_Reduce_Mixed_Unique_And_Duplicates(self):
      fileList = ["a", "e", "b", "c", "d", "a", "b", "b", "a", "b"]
      answer = self.sut.optimizeListOfFiles(fileList)
      unique = answer[0]
      dups = answer[1]
      self.assertEquals(len(unique), 3, "wrong size of unique elements")
      self.assertEquals(unique[0], "c", "wrong unique element at index 0: " + unique[0] )
      self.assertEquals(unique[1], "d", "wrong unique element at index 1: " + unique[1] )
      self.assertEquals(unique[2], "e", "wrong unique element at index 2: " + unique[2] )

      self.assertEquals(len(dups), 7, "wrong size of duplicate elements")
      self.assertEquals(dups[0], "a", "wrong dups element at index 0: " + dups[0] )
      self.assertEquals(dups[1], "a", "wrong dups element at index 1: " + dups[1] )
      self.assertEquals(dups[2], "a", "wrong dups element at index 2: " + dups[2] )
      self.assertEquals(dups[3], "b", "wrong dups element at index 3: " + dups[3] )
      self.assertEquals(dups[4], "b", "wrong dups element at index 4: " + dups[4] )
      self.assertEquals(dups[5], "b", "wrong dups element at index 5: " + dups[5] )
      self.assertEquals(dups[6], "b", "wrong dups element at index 6: " + dups[6] )

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
      newUpdateStatement = """UPDATE statistics LEFT JOIN urls ON urls.id = statistics.url"""
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
        warning("Length Input File List: " + str(len(fullFilePath)))
        warning("Number of Rows Updated: " + str(result))
        warning("|".join(fullFilePath) + "|")
      else:
          debug("All rows accounted for, committing update")
          dbConnection.commit()
          
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
  def convertListToString(self, listOfFiles):
    return ' '.join([str(x) for x in listOfFiles])
  
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
  # Given a list of strings (for example: a text file), read through the 
  # list of files and bucketize the lines so that an optimized set of
  # calls can be made to increment playcount.
  #
  # The file content is expected to be in the format of the full file path
  # separated by the pipe character followed by the playcount.  For example:
  #
  # /home/pub/audio/Sharon Jones and the Dap Kings/I Learned the Hard Way/
  # /home/pub/audio/NumeroGroup/Purple Snow: Forecasting the Minneapolis Sound/ | 2
  # /home/pub/audio/Carlo Coupe/Mis Balas Llevan Tu Nombre/|2
  # /home/pub/audio/AndrewKelly/SongsMadeForRza/
  # /home/pub/audio/Big Boi/MashupMondays/
  # /home/pub/audio/Jason James & Rodney Hazard/Marvelous World Of Color/
  # /home/pub/audio/MoKolours/MoKolours/|3
  # /home/pub/audio/Classic Blaxploitation OST/Foxy Brown (1974)/|3
  #
  # While the script could simply call each line one at a time, it would be better
  # to group some of the file increases together by playcount.  So all the files 
  # that get one increment are done together, then all the files to bump by 
  # two, etc...
  #
  #
  #
  def optimizeBatch(self, listOfFiles):
      intermediate = dict()
      for line in listOfFiles:
          strippedline = line
          strippedline = strippedline.replace("\n", "")
          strippedline = strippedline.strip()
          strippedline = strippedline.strip("\n")
          pieces = strippedline.split("|")
          if pieces[0] == "":
              continue
          elif len(pieces) == 1:
              pieces.append("1")
          elif len(pieces) < 1 or len(pieces) > 2:
              debug("Skipping line: \"" + strippedline + "\"")
              continue
          
          filePath = pieces[0].strip()
          playcount = pieces[1].strip()
          if filePath in intermediate:
              debug("Incrementing '" + filePath + "'")
              intermediate[filePath] += int(playcount)
              debug("   Count is now '" + str(intermediate[filePath]) + "'")
          else:
              debug("Adding Entry for '" + filePath + "'")
              intermediate[filePath] = int(playcount)
              debug("   Count is '" + str(intermediate[filePath]) + "'")
      
      # After reading the initial list, now reduce the
      # entries 
      answer = dict()
      fileEntries = sorted(intermediate.keys())
      for fileEntry in fileEntries:
          bumpNumber = intermediate[fileEntry]
          if bumpNumber in answer:
              answer[bumpNumber].append(fileEntry)
          else:
              answer[bumpNumber] = [fileEntry]
      
      return answer
  #######################################################################
  #
  # Optimize list of files
  #
  # Much like optimizeBatch (which is for the input from the batch file),
  # this function is for a second, internal reduce given a (big) set of
  # full filepaths, the unique entries should be separated from the 
  # duplicate entries as otherwise the bulk-update to the SQL command
  # will fail to recognize the duplicate file paths properly.
  #
  # To workaround this issue, files that are duplicated will be removed
  # from the bulk batch.  The output of this method is too lists.
  # (1) the first list is a list of unique entries
  # (2) the second list is a list of the duplicates 
  #
  # For example: given the input [a b c b d e b], the results would be
  #    [a c d e]
  #    [b b b]
  def optimizeListOfFiles(self, fileSet):
      noDuplicates = []
      individualUpdates = []
      if len(fileSet) > 0:
        duplicates = findDuplicates(fileSet)
        unique = findUnique(fileSet)
        noDuplicates = [n for n in unique if n not in duplicates]
        individualUpdates = [n for n in fileSet if n in duplicates]
      return [sorted(noDuplicates), sorted(individualUpdates)]
  
#######################################################################
#
# Establish a connection to the Amarok database
#
def connectToDatabase():
  readDefaultFile = os.path.abspath(os.getcwd())
  readDefaultFile = os.path.join(readDefaultFile, "mysql.pyAmarokBump.cnf")
  debug("Reading Database information from " + readDefaultFile)
  return MySQLdb.connect(read_default_file=readDefaultFile)

#######################################################################
#
# Prints debugging messages (if the debugging flag has been set)
#
def debug(message):
  if DEBUG_FLAG == "true":
    #print(message)
    print message

#######################################################################
#
# Batch update of a set of files
#
def batchBumpAmarokStats(connection, fileSet, playCountBump, message):
    if len(fileSet) > 0:
        bump = BumpAmarokStatistics()
        uniqsAndDups = bump.optimizeListOfFiles(fileSet)
        noDuplicates = uniqsAndDups[0]
        debug(message + " to bulk update by " + str(playCountBump) + ": "+ str(len(noDuplicates)))
        debug(noDuplicates)
        if len(noDuplicates) > 0:
            bumpAmarokStats(connection, noDuplicates, playCountBump)
        
        #
        # Duplicates (could be duplicated once or may be more) should
        # be done one at a time
        individualUpdates = uniqsAndDups[1]
        debug(individualUpdates)
        debug(message + " to individually update by " + str(playCountBump) + ": "+ str(len(individualUpdates)))
        for duplicate in individualUpdates:
            bumpAmarokStats(connection, [duplicate], playCountBump)

#######################################################################
#
# Update of a set of files
#
def bumpAmarokStats(connection, fileOrDirectory, playCountBump):
  bump = BumpAmarokStatistics()
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
# Run Unit Test Suite
#
def runFunctionalTests():
  suite = unittest.TestLoader().loadTestsFromTestCase(FunctionalTestFunctions)
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
  print "To use a batch file where the with file entries execute the following:"
  print ""
  print "\t" + SCRIPT_NAME + " --batchfile=<path to file>"
  print ""
  print "The batchfile format is 'filepath|<playCountBump>', i.e.: "
  print "     /home/pub/audio/Big Boi/MashupMondays/|2 "

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
                 ["help", "debug",  "batchfile=", "pretend", "playcount-bump=", "unit", "unittest", "unittests", "unit-test", "unit-tests", "functional", "functionaltest", "functionaltests", "functional-test", "functional-tests" ])
  except getopt.GetoptError as err:
    # print help information and exit:
    warning(str(err))
    usage()
    sys.exit(2)
  #######################################################################
  #
  # Parse Command-Line Options and Arguments
  #
  pathToBatchFile = ""
  playCountBump = 0
  for o, a in opts:
    if o in ("-h", "--help"):
      usage()
      sys.exit()
    elif o in ("-d", "--debug"):
      global DEBUG_FLAG
      DEBUG_FLAG = "true"
    elif o in ("--batchfile"):
      global BATCH_FLAG
      BATCH_FLAG = "true"
      pathToBatchFile = a
    elif o in ("-p", "--pretend"):
      global PRETEND_FLAG
      PRETEND_FLAG = "true"
    elif o == "--playcount-bump":
      playCountBump = int(a)
    elif o in ("--unit", "--unittest", "--unittests", "--unit-test", "--unit-tests",):
      global UNITTEST_FLAG
      UNITTEST_FLAG = "true"
    elif o in ("--functional", "--functionaltest", "--functionaltests", "--functional-test", "--functional-tests"):
      global FUNCTIONAL_TEST_FLAG
      FUNCTIONAL_TEST_FLAG = "true"
    else:
      assert False, "unhandled option"
    
  #######################################################################
  #
  # Sanity checks 
  #
  debug(str(args))
  if UNITTEST_FLAG == "true":
    runUnitTests()
  elif FUNCTIONAL_TEST_FLAG == "true":
    runFunctionalTests()
  elif BATCH_FLAG == "false" and len(args) == 0:
    warning("Missing command-line arguments")
    usage()
  elif BATCH_FLAG == "false" and playCountBump < 1:
    warning("A positive playcount bump number must be specified")
    usage()
  elif BATCH_FLAG == "true" and playCountBump != 0:
    warning("The flags '--batchfile' and --playcount-bump' may not be used together")
  elif BATCH_FLAG == "true" and not(os.path.isfile(pathToBatchFile)):
    warning("The batch file '"+pathToBatchFile+"' does not exist")
  else:
    debug("\n\rConnecting to database")
    connection = connectToDatabase()
    
    try:
      fileBumpMap = dict()
      
      if BATCH_FLAG == "true":
          bump = BumpAmarokStatistics()
          try:
              f = open(pathToBatchFile, 'r')
              fileBumpMap = bump.optimizeBatch(f)
          finally:
              f.close()
      else: 
          fileBumpMap[playCountBump] = args
      
      for number in fileBumpMap.keys():
          updateDirectoryList = []
          updateFileList = []
          debug("key:   " + str(number))
          paths = fileBumpMap[number]
          debug("value: " + str(paths))
          bumpInfo =  [connection, number]
          
          for path in paths:
              debug("path:" + str(path))
              fileOrDirectory = string.lstrip(path, "\"")
              fileOrDirectory = string.rstrip(fileOrDirectory, "\"")
              
              # Need full path for deciding if this is a file or a directory
              if os.path.isdir(fileOrDirectory):
                  fileSet = findv2(bumpInfo, fileOrDirectory, os.listdir(fileOrDirectory))
                  updateDirectoryList += fileSet
              else:
                  updateFileList.append(fileOrDirectory)
          
          # Batch update of all elements
          # Because directories were found recursively, there could be duplicates.
          # This can cause problems when updating, so for both files and directories
          # there needs to be a workaround
          batchBumpAmarokStats(connection, updateDirectoryList, number, "Number of files from directories")
          batchBumpAmarokStats(connection, updateFileList, number, "Number of individual files")
          
    finally:
      debug("Closing connection to database")
      connection.close()

if __name__ == "__main__":
    main()
