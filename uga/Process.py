## Copyright (c) 2015 Ryan Koesterer GNU General Public License v3
##
##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import psutil
import subprocess

class Error(Exception):
	def __init__(self, msg):
		self.msg = 'ERROR: ' + msg

def PrintError(e):
	return "\nERROR: " + e + "\n"

def Highlight(m):
	return "\n   ... " + m + "\n"
	
def Bold(m):
	return "\033[1m" + m + "\033[0m"

def Qsub(qsub_pre,cmd):
	try:
		p = subprocess.Popen(qsub_pre + [cmd[1:-1]],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
		for line in iter(p.stdout.readline, ''):
			sys.stdout.write(line)
		p.wait()
	except KeyboardInterrupt:
		kill_all(p.pid)
		print "   ... process terminated by user"
		sys.exit(1)

def Interactive(submit, cmd, log_file = None):
	try:
		p = subprocess.Popen([submit,cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
		if log_file:
			log = open(log_file, 'w')
		for line in iter(p.stdout.readline, ''):
			sys.stdout.write(line)
			if log_file:	
				log.write(line)
		p.wait()
		if log_file:
			log.close()
	except KeyboardInterrupt:
		kill_all(p.pid)
		print "   ... process terminated by user"
		sys.exit(1)

def kill_all(pid):
	parent = psutil.Process(pid)
	for child in parent.children(recursive=True):
		child.kill()
	parent.kill()