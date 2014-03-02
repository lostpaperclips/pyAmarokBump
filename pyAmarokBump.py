# -*- coding: utf-8 -*-
import getopt, MySQLdb, os, string, subprocess, sys, time, urllib

VERSION  = "0.0.1"
DEBUG_FLAG = "false"
PRETEND_FLAG = "false"
SCRIPT_NAME = "pyAmBump-" + VERSION + ".py"

#######################################################################
#
# args: extention to find
# dirname: name of current directory
# list of files in the current directory
#
def find(bump, dirname, names):
  debug("\n\rEntering find()")
  debug("  bump = " + str(bump))
  debug("  dirname = " + dirname)
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
      bumpAudioPlaycount(bump[0], fullFilePath, bump[1])
  return foundAudioFiles

#######################################################################
#
# Update the statistics table
#
# For the given (Amarok) database connection, increase the playcount by
# the given bump number
#
def bumpAudioPlaycount(dbConnection, fullFilePath, bump):
  debug("\n\ra) find id from the url/path")
  cursor = dbConnection.cursor()
  try:
    findUrlIdStatement = """
    SELECT id FROM urls WHERE 
    urls.rpath = ".""" + fullFilePath + """";"""
    executeSelectStatement(cursor, findUrlIdStatement)
    debug("curor.rowcount : " + str(cursor.rowcount))
    createAndAccessDate = str(int(time.time()))
    
    if cursor.rowcount != 1:
      warning("No entry in url table for " + fullFilePath)
    else:
      debug("\n\rb) update/add current playcount")
      findUrlIdResult =  cursor.fetchall()
      urlId = str(findUrlIdResult[0][0])   
      
      # find the appropriate entry in the statistics table and updatePlaycountStatement
      findStatisticsIdStatement = """SELECT id FROM statistics WHERE statistics.url = """ + urlId + """;"""
      executeSelectStatement(cursor, findStatisticsIdStatement)

      if cursor.rowcount == 0:
        debug("\n\rc - i) create playcount record")   
        debug("Inserted play count will be " + str(int(bump)))
        insertPlaycountStatement = """INSERT INTO statistics (url,createdate,accessdate,score,rating,playcount) VALUES(""" + \
                                   urlId + """, """ + createAndAccessDate + """, """ + createAndAccessDate + \
                                   """, 0, 0, """ + str(bump)  + """);""" 
        findPlayCountResult = executeInsertStatement(cursor, insertPlaycountStatement)
      
      else:
        debug("\n\rc - ii) update/add current playcount")
        findPlaycountResult =  cursor.fetchall()
        dbPlayCount = findUrlIdResult[0][0]
        debug("Current playcount is " + str(dbPlayCount))
        debug("Updated play count will be " + str(dbPlayCount + int(bump)))
        updatePlaycountStatement = """UPDATE statistics SET statistics.playcount = statistics.playcount + """ \
                                   + str(bump) 
        updatePlaycountStatement = updatePlaycountStatement + """, statistics.accessdate = """ \
                                   + createAndAccessDate
        updatePlaycountStatement = updatePlaycountStatement + """ WHERE statistics.url = """ \
                                   + urlId + """;"""
        findPlayCountResult = executeUpdateStatement(cursor, updatePlaycountStatement)

  except Exception as detail:
    warning(str(detail))
    debug("Error while updating record for : " + fullFilePath)
  finally:
    debug("Closing the cursor")
    cursor.close()


#######################################################################
#
# Run a SQL INSERT statement
#
def executeInsertStatement(cursor, statement):
  debug("Running INSERT = '" + statement +"'")
  if PRETEND_FLAG == 'false':
    cursor.execute (statement)
    debug("Executed INSERT = '" + statement +"'") 
  debug("Number of rows found from INSERT: " + str(cursor.rowcount))

#######################################################################
#
# Run a SQL SELECT statement
#
def executeSelectStatement(cursor, statement):
  debug("Running SELECT = '" + statement +"'") 
  cursor.execute (statement)
  debug("Executed SELECT = '" + statement +"'") 
  debug("Number of rows found from SELECT: " + str(cursor.rowcount))

#######################################################################
#
# Run a SQL UPDATE statement
#
def executeUpdateStatement(cursor, statement):
  debug("Running UPDATE = '" + statement +"'")
  if PRETEND_FLAG == 'false':
    cursor.execute (statement)
    debug("Executed UPDATE = '" + statement +"'")
  debug("Number of rows found from UPDATE: " + str(cursor.rowcount))

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
    print message
    
#######################################################################
#
# Prints warning messages to STDERR
#
def warning(message):
  print >> sys.stderr, "WARNING : " + message

#######################################################################
#
# Print Usage Information
#
def usage():
  print
  print "Usage information"
  print
  print "To increase the playcount of a directory of audio files, "
  print "execute the following:"
  print
  print "\t" + SCRIPT_NAME + "  --playcount-bump=<number> [Path to File(s)]"  

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
    opts, args = getopt.getopt(sys.argv[1:], "hdp", ["help", "debug", "pretend", "playcount-bump="])
  except getopt.GetoptError, err:
    # print help information and exit:
    print >> sys.stderr, err
    usage()
    sys.exit(2)
  #######################################################################
  #
  # Parse Command-Line Options and Arguments
  # 
  playCountBump = 0
  for o, a in opts:
    if o in ("-h", "--help"):
      usage()
      sys.exit()
    elif o in ("-d", "--debug"):
      global DEBUG_FLAG
      DEBUG_FLAG = "true"
    elif o in ("-p", "--pretend"):
      global PRETEND_FLAG
      PRETEND_FLAG = "true"
    elif o == "--playcount-bump":
      playCountBump = a
    else:
      assert False, "unhandled option"
  #######################################################################
  #
  # Sanity checks 
  #
  if len(args) == 0:
    print >> sys.stderr, "Missing command-line arguments"
    usage()
  elif playCountBump < 1:
    print >> sys.stderr, "A positive playcount bump number must be specified"
    usage()
  else:
    debug("Connecting to database")
    connection = connectToDatabase("localhost", "amarok2 ", "amarok2", "fri-(cab)")
    try:
      bumpInfo =  [ connection, playCountBump]
      os.path.walk(string.join(args), find, bumpInfo)
    finally:
      debug("Closing connection to database")
      connection.close()

if __name__ == "__main__":
    main()
