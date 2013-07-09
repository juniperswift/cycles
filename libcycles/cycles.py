#!/usr/bin/python

from __future__ import division
import os
import sys
import sqlite3 as sqlite
from datetime import datetime,timedelta

DEBUG=False


def dt_to_ts(dt):
	if dt:
		return int(dt.strftime("%s"))
	else:
		return -1

class Cycle:
	'A class representation of a menstrual cycle'
	
	def __init__(self, start_dt, period_end_dt = None, next_cycle = None, previous_cycle = None, db_id = None):
		'Constructor'
		self.start_dt = start_dt
		self.period_end_dt = period_end_dt
		self.next = next_cycle
		self.prev = previous_cycle
		self.db_id = db_id

    
	@property
	def length(self):
		'Returns cycle length in days as a float'
		if self.next:
			length_td = self.next.start_dt - self.start_dt
			return length_td.days + length_td.seconds/86400
		else:
			return None

	@property
	def period_length(self):
		'Returns period length in days  b as a float'
		if self.period_end_dt:
			length_td = self.period_end_dt - self.start_dt
			return length_td.days + length_td.seconds/86400
		else:
			return None	

	def save(self,con=None):
		if con:
			start_dt_ts = dt_to_ts(self.start_dt)
			period_end_dt_ts = dt_to_ts(self.period_end_dt)
			sqlcur = con.cursor()
			if DEBUG:
				print "Saving cycle(%s): start_dt=%s, period_end_dt=%s"%(self.db_id,start_dt_ts,period_end_dt_ts)
			if not self.db_id:
				sqlcur.execute("INSERT into cycles(start_dt,period_end_dt) VALUES(?,?)",(start_dt_ts,period_end_dt_ts if period_end_dt_ts != -1 else "null"))
				if DEBUG:
					print "[Inserted %s into database. id = %s]"%(start_dt_ts,sqlcur.lastrowid)
				self.db_id = int(sqlcur.lastrowid)
			else:
				sqlcur.execute("UPDATE cycles SET start_dt=?, period_end_dt=? WHERE id=?",(start_dt_ts,period_end_dt_ts if period_end_dt_ts != -1 else "null",self.db_id))

			con.commit()

	def __iter__(self):
		return self

	def next(self):
		if not self.next:
			raise StopIteration
        
		return self.next
    
	def __cmp__(self,other):
		if not other:
			return 1
		return (self.start_dt - other.start_dt).days
    
	def __repr__(self):
		return repr((self.start_dt,self.next.start_dt if self.next else None,self.prev.start_dt if self.prev else None))
    
	def __str__(self):
		length_str = str(round(self.length,2)) if self.length else "--"
		period_length_str = str(round(self.period_length,2)) if self.period_length else "--"
		end_dt_str = self.next.start_dt.strftime("%Y-%m-%d %H:%M") if self.next else None
		return "%s: [%s, next_cycle = %s, previous_cycle = %s] Length: %s / Period length: %s"%(self.db_id,self.start_dt.strftime("%Y-%m-%d %H:%M"),end_dt_str, self.prev.start_dt if self.prev else None, length_str,period_length_str)


class Cycles:
	
	def __init__(self,path_to_database="cycles.db",db_type="sqlite"):
		self.head = None
		self.tail = None
		self.db_path = path_to_database
		self.db_type = db_type
		if self.db_type == "sqlite":
			self.con = self.load_from_sqlite()

	def __enter__(self):
		return
		

	def __exit__(self, type, value, traceback):
		if self.db_type == "sqlite":
			self.con.commit()
			self.con.close()

    
	def load_from_sqlite(self):
		if not os.path.exists(self.db_path):
			if not os.path.exists(os.path.dirname(self.db_path)):
				try:
					if os.path.dirname(self.db_path) != '':
						os.makedirs(os.path.dirname(self.db_path))
				except Exception,e:
					if DEBUG:
						print "%s - Could create database directory. Exiting."%e
					exit()
			try:
				open(self.db_path, 'a').close()
				con = sqlite.connect(self.db_path)
				cur = con.cursor()
				cur.execute("CREATE TABLE cycles(id INTEGER PRIMARY KEY, start_dt INTEGER, period_end_dt INTEGER)")
				if DEBUG:
					print("[Database created at {}]".format(self.db_path))
				return con
			except Exception,e:
				if DEBUG:
					print "%s - Could create database. Exiting."%e
				exit()
        
		con = sqlite.connect(self.db_path)
		cur = con.cursor()
		cur.execute("SELECT id,start_dt,period_end_dt FROM cycles order by start_dt desc")
		rows = cur.fetchall()
        
		if len(rows) > 0:
			next_cycle = None
			for i in range(len(rows)):
                
				start_dt = datetime.fromtimestamp(rows[i][1])
				period_end_dt = datetime.fromtimestamp(rows[i][2]) if rows[i][2] != 'null' and rows[i][2] != None else None
				cycle = Cycle(start_dt=start_dt,period_end_dt=period_end_dt,next_cycle=next_cycle,db_id = int(rows[i][0]))
                
				self.add_to_head(cycle)

		if DEBUG:
			print "[Successfully loaded database from %s]"%self.db_path
		
		return con

	def add_to_head(self,cycle):
		if not self.head:
			self.head = cycle
			self.tail = cycle
		else:
			cycle.next = self.head
			self.head.prev = cycle
			self.head = cycle

	def add_to_tail(self,cycle):
		if not self.tail:
			self.head = cycle
			self.tail = cycle
		else:
			cycle.prev = self.tail
			tail.next = cycle
			self.tail = cycle
    
	def new_cycle(self,start_dt,period_end_dt=None):
		new_cycle = Cycle(start_dt,period_end_dt)
		
		if self.insert_cycle(new_cycle):
			new_cycle.save(self.con)
			return new_cycle
		else:
			return None


	@property
	def lengths(self):
		cur = self.head
		valid_lengths = []
		while cur:
			if cur.length >= 21 and cur.length <= 35:
				valid_lengths.append(cur.length)
			cur = cur.next
		return valid_lengths

	@property
	def avg_cycle_length(self):
		if len(self.lengths) > 0:
			return float(sum(self.lengths))/len(self.lengths)
		else:
			return 0

	@property
	def avg_period_length(self):
		period_lengths = []
		cur = self.head
		while cur:
			if cur.period_length:
				period_lengths.append(cur.period_length)
			cur = cur.next

		if len(period_lengths) > 0:
			return float(sum(period_lengths))/len(period_lengths)
		else:
			return 0

	def to_list(self,reverse=False):
		a_list = []
		cur = self.head
		while cur:
			if reverse:
				a_list.insert(0, cur)
			else:
				a_list.append(cur)
			cur = cur.next

		return a_list

	@property
	def count(self):
		return len(self.to_list())

	@property
	def shortest_cycle(self):
		shortest_cycle = self.head
		cur = self.head.next
		while cur:
			if cur.length and cur.length < shortest_cycle.length:
				shortest_cycle = cur
			cur=cur.next
		return shortest_cycle

	@property
	def longest_cycle(self):
		longest_cycle = self.head
		cur = self.head.next
		while cur:
			if cur.length > longest_cycle.length:
				longest_cycle = cur
			cur=cur.next
		return longest_cycle

	def save(self):
		if DEBUG:
			print "[Saving cycles to %s database]"%self.db_type
		if self.db_type == "sqlite":
			cur = self.head
			while cur:
				cur.save(self.con)
				cur = cur.next
				
			self.con.commit()

	def get_cycle(self,cycle_id):
		cycle = None
		cur = self.head
		while cur:
			if cur.db_id == cycle_id:
				cycle = cur
				break
			cur = cur.next

		return cur

	def edit_cycle(self, cycle, start_dt = None, period_end_dt = None):
		if cycle and start_dt:
			cycle.start_dt = start_dt
			if (cycle.next and cycle > cycle.next) or (cycle.prev and cycle < cycle.prev):
				self.remove_from_list(cycle)
				self.insert_cycle(cycle)

		if cycle and period_end_dt:
			cycle.period_end_dt = period_end_dt

		cycle.save(self.con)

		return cycle 

	def remove_from_list(self,cycle):
		if cycle:
			if cycle.prev:
				cycle.prev.next = cycle.next
			if cycle.next:
				cycle.next.prev = cycle.prev
			if self.head == cycle:
				self.head = cycle.next
			if self.tail == cycle:
				self.tail = cycle.prev
			cycle.next = None
			cycle.prev = None
			
	def insert_cycle(self,cycle):
		if not self.head:
			self.head = cycle
			self.tail = cycle
		else:
			cur = self.head
			while cur:
				if cycle < cur and not cur.prev:
					cycle.next = cur
					cur.prev = cycle
					self.head = cycle
					break
				elif cycle > cur and not cur.next:
					cur.next = cycle
					cycle.prev = cur
					self.tail = cycle
					break
				elif cycle > cur and cycle < cur.next:
					cycle.next = cur.next
					cycle.prev = cur
					cur.next.prev = cycle
					cur.next = cycle
					break
				elif cycle == cur:
					if DEBUG:
						print "Cycle already exists!"
					return False

				cur = cur.next
				
		return True
		
	def delete_cycle(self,cycle):
		if cycle:
			self.remove_from_list(cycle)

			if cycle.db_id:
				sqlcur = self.con.cursor()
				sqlcur.execute("DELETE FROM cycles WHERE id=?",(cycle.db_id,))
				self.con.commit()

	def delete_all(self):
		if DEBUG:
			print "[Deleting all cycles]"

		cur = self.head
		sqlcur = self.con.cursor()
		while cur:
			next = cur.next
			self.delete_cycle(cur)
			cur = next

		self.head = None
		self.tail = None

		#os.remove(self.db_path)

		self = None

    
	def __repr__(self):
		return repr(self.cycles)
    
    
	def __str__(self):
		ret = "Cycles: (%s, count: %d, avg_length: %s, avg_period_length: %s)\n"%(self.db_path,self.count,round(self.avg_cycle_length,1),round(self.avg_period_length,1))
		cur = self.head
		while cur:
			ret += "\t" + str(cur) + "\n"
			cur = cur.next
		return ret

if __name__ == "__main__":

	DEBUG=True


	db_path = None
	cycles1 = None
	cycles2 = None
	if len(sys.argv) > 1:
		db_path = sys.argv[1]
		cycles1 = Cycles(db_path,"sqlite")
		print cycles1
	try:
		cycles2 = Cycles("cycles.db","sqlite")
		print cycles2

		print ""
		raw_input("Press enter to continue...")

		print "Compaing two Cycles..."
		prev_cycle = Cycle(datetime(2013,05,01,0,0,0))
		next_cycle = Cycle(datetime(2013,06,01,0,0,0))
		print "%s is less than %s: %s"%(prev_cycle.start_dt, next_cycle.start_dt, prev_cycle < next_cycle)
		prev_cycle = Cycle(datetime(2013,05,01,0,0,0))
		next_cycle = Cycle(datetime(2013,05,01,0,0,0))
		print "%s equals %s: %s"%(prev_cycle.start_dt, next_cycle.start_dt, prev_cycle == next_cycle)
		prev_cycle = Cycle(datetime(2013,05,01,0,0,0))
		next_cycle = Cycle(datetime(2013,04,01,0,0,0))
		print "%s is greater than %s: %s"%(prev_cycle.start_dt, next_cycle.start_dt, prev_cycle > next_cycle)

		print ""
		raw_input("Press enter to continue...")
	    
		print ""
		print "Adding a cycle for today..."
		today = datetime.today()
		cycle1 = cycles2.new_cycle(today,today+timedelta(days=7))
		print cycles2

		print ""
		print "Get cycle and print"
		print cycles2.get_cycle(1)

		print ""
		raw_input("Press enter to continue...")
	    
		print "Adding a cycle for 80 days in the past..."
		minus_84_days = datetime.today() - timedelta(days=75)
		cycle2 = cycles2.new_cycle(minus_84_days,minus_84_days+timedelta(days=8))
		print cycle2

		print ""
		print "Deleting cycle1..."
		cycles2.delete_cycle(cycle1)
		print cycles2

		print ""
		raw_input("Press enter to continue...")

		print ""
		print "Editing cycle 2..."
		cycles2.edit_cycle(cycle2,period_end_dt=minus_84_days+timedelta(days=5))
	    
		print "Adding a cycle for 20 days in the past..."
		minus_27_days = datetime.today() - timedelta(days=20)
		cycle3 = cycles2.new_cycle(minus_27_days,minus_27_days+timedelta(days=6))
		print cycle3

		print "Adding a cycle for 26 days in the future..."
		plus_26_days = datetime.today() + timedelta(days=26)
		print cycles2.new_cycle(plus_26_days,plus_26_days+timedelta(days=5))

		print ""
		raw_input("Press enter to continue...")

		print "Adding a cycle for 50 days in the past..."
		minus_56_days = datetime.today() - timedelta(days=50)
		cycles2.new_cycle(minus_56_days,minus_56_days+timedelta(days=5))

		minus_100_days = datetime.today() - timedelta(days=100)
		cycles2.edit_cycle(cycle3,start_dt=minus_100_days,period_end_dt=minus_100_days+timedelta(days=7))

		print cycles2

		print ""
	except Exception,e:
		print e
		print "Opps! Something went wrong. Deleting database..."
		os.remove("cycles.db")
	finally:
		raw_input("Press enter to delete all cycles...")

		if cycles2:
			cycles2.delete_all()
			print cycles2
			os.remove("cycles.db")
	

