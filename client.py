from clientNFS import *
from time import *

def Main():
	print "==========================="
	print "Get directory service info "
	#address = raw_input("Address: ")
	address = "192.168.1.2"
	port = int(raw_input("Port: "))
	mynfs_set_srv_addr(address, port)
	print "==========================="
	
	secs = int(raw_input("Set time for cache validity: "))
	mynfs_set_cache_validity(secs)

	print "==========================="
	print "			  MENU"
	print "			-> NFS Check"
	print "			-> open"
	print "			-> read"
	print "			-> write"
	print "			-> seek"
	print "			-> close"
	print "==========================="

	while True:
		option = raw_input(">	")
		if option == "open":
			filename = raw_input("Filename: ")
			flags = raw_input("Flags (e.g. O_CREAT O_RDWR ...): ")
			flags = flags.split(" ")
			flag = 0
			for fl in flags:
				if fl == "O_CREAT":
					flag |= O_CREAT
				elif fl == "O_EXCL":
					flag |= O_EXCL
				elif fl == "O_TRUNC":
					flag |= O_TRUNC
				elif fl == "O_RDWR":
					flag |= O_RDWR
				elif fl == "O_RDONLY":
					flag |= O_RDONLY
				elif fl == "O_WRONLY":
					flag |= O_WRONLY
				else:
					print "Invalid Flag"
	
			fd = mynfs_open(filename, flag)
			if fd != -1:
				print "Fd for " + filename + " is " + str(fd)
			else:
				print "Error"
		elif option == "read":
			fd = int(raw_input("Fd: "))
			n = int(raw_input("Read size: "))
			length, buf = mynfs_read(fd, n)
			if length != -1:
				print "You read: " + buf + " (size = " + str(length) + ")"
			else:
				print "Error"
		elif option == "write":
			fd = int(raw_input("Fd: "))
			buf = raw_input("Input to write: ")
			n = int(raw_input("Size of input: "))
			length = mynfs_write(fd, buf, n)
			if length != -1:
				print "You wrote: " + str(length) + " bytes"
			else:
				print "Error"
		elif option == "seek":
			fd = int(raw_input("Fd: "))
			pos = int(raw_input("Pos: "))
			whence = raw_input("Whence: ")

			if whence == "SEEK_SET":
				flag = SEEK_SET
			elif fl == "SEEK_CUR":
				flag = SEEK_CUR
			elif fl == "SEEK_END":
				flag = SEEK_END
			pos = mynfs_seek(fd, pos, flag)
			if pos != -1:
				print "You moved fd in pos: " + str(pos)
			else:
				print "Error"
		elif option == "close":
			fd = int(raw_input("Fd: "))
			
			check = mynfs_close(fd)
			if check != -1:
				print "You successfully closed fd"
			else:
				print "Error"
		elif option == "NFS Check":
			print "Create 2 copies of the given file one in the directory of the server and the other in the local directory"
			filename = raw_input("Filename: ")
			size = int(raw_input("File size: "))

			file = open("__"+filename, O_CREAT|O_RDWR)
			fd2 = mynfs_open("new_"+filename, O_CREAT|O_RDWR)
			fd = mynfs_open(filename, O_CREAT|O_RDWR)
			print fd
			print fd2
			if fd != -1 and fd2 != -1:
				length, buf = mynfs_read(fd, size)
				if length != -1:
					size = write(file, buf)
					length = mynfs_write(fd2, buf, size)
				else:
					print "Error in mynfs_read"
			else:
				print "Error in mynfs_open"

		else:
			print "Wrong input, try again :)"
	
		
            
if __name__ == '__main__' :
	Main()