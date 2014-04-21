-- 
--
--# 1) Uncomment the GRANT line
--# 2) Change the password
--# 3) From a bash prompt, execute: mysql -u root -p < create_database.sql

CREATE DATABASE pyAmarokBump;
GRANT ALL PRIVILEGES ON pyAmarokBump.* TO 'pyAmarmokBump' IDENTIFIED BY 'password'; FLUSH PRIVILEGES;
