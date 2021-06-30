#
# Silo -- a simple, general purpose file system for LSL via HTTP
#  version 2021-06-29
#  by John Dougan
#    
#  Copyright (c) 2021 John Dougan
#  Licensed under the "MIT" open source license.
#
#  This file is only part of the whole distribution.
#    Makefile -- Config for Replit.
#
# Makefile for development on Replit in a PHP Web Server repl.
# Unzip ito the repl, move file to root, then make all
# Start the PHP server via the run button, make tests
#
all: replit
	mkdir -p data
#
# Test againt the local silo.
# 
tests:
	# rm -rf data/*
	python3 test.py http://localhost:8000/silo.php 2> test.log
#
clean:
	rm -rf test.log data .replit
#
replit:
	echo 'run = "php -S 0.0.0.0:8000 -t ." ' > .replit 
