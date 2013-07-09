#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import sqlite3 as lite
from dateutil.parser import *
from dateutil.tz import *
from datetime import *
import time
import sys
import os
from libcycles import Cycles

def list_commands():
    print ""
    print "  Type 'new' to log a cycle."
    print "  Type 'list' to show all cycles."
    print "  Type 'stats' to show information on cycle history."
    print "  Type 'edit' to edit a cycles start date or period end date."
    print "  Type 'quit' to save and exit."

def display_menu():
    print ""
    print "  Type 'help' for a list of commands."
    return raw_input("> ")
    
def ask_for_dt(question):
    'Returns a datetime based on an input (defaults to datetime.today())'
    now = datetime.today()
    date_str = raw_input("%s [%s]? "%(question,now.strftime('%b %d, %Y %H:%M')))
    if (date_str == ""):
        return now
    else:
        try:
            return parse(date_str)
        except Exception,e:
            print "That date is invalid: %s. Please try again."%e
            return ask_for_dt(question)

def new(cycles):
    new_start_dt = ask_for_dt("When did the cycle start")
    if new_start_dt:
        if new_start_dt > datetime.today():
            print "That date is in the future. Please try again."
            new(cycles)
            return False
        cycles.new_cycle(new_start_dt)
    return True
    
def edit(cycles):
    cycle_list = cycles.to_list(reverse=True)

    if len(cycle_list) == 0:
        print "You must log a cycle before you can edit."
        return False
    print "|---------- Cycles ------------|"
    print "|  # | Start Date | Period End |"
    for i in range(len(cycle_list)): 
        cycle = cycle_list[i]
        start_dt = cycle.start_dt
        period_end_dt_str = "--"
        if cycle.period_end_dt:
            period_end_dt_str = cycle.period_end_dt.strftime("%Y-%m-%d")
        print "| %2s | %10s | %10s |"%(i+1,start_dt.strftime("%Y-%m-%d"),period_end_dt_str)
    print "|---------------------------------|"
    cycle_idx = raw_input("Which cycle would you like to edit (enter '0' to cancel) [1]? ")
    if cycle_idx == '0':
        return
    if cycle_idx == '':
        cycle_idx = 0
    else:
        cycle_idx = int(cycle_idx)-1
    if cycle_idx >= 0 and cycle_idx < len(cycle_list):
        cycle = cycle_list[cycle_idx]

        new_start_dt = cycle.start_dt
        new_period_end_dt = cycle.period_end_dt

        print "\nCurrent start date: %s"%new_start_dt.strftime("%Y-%m-%d")
        print "Current last day of period: %s"%(new_period_end_dt.strftime("%Y-%m-%d") if new_period_end_dt != None else "--")
        choice = raw_input("\n1) Edit start date\n2) Edit last day of period\n3) Delete this cycle\n0) Cancel\n > ")
        if choice == '1':
            new_start_dt = ask_for_dt("What date did the cycle start")
        elif choice == '2':
            new_period_end_dt = ask_for_dt("What was the last day of the period starting on %s"%new_start_dt.strftime("%b %d, %Y"))
        elif choice == '3':
            delete_cycle(cycles,cycle)
            return True
        cycles.edit_cycle(cycle,start_dt=new_start_dt,period_end_dt=new_period_end_dt)
    
    return True
        
def delete_cycle(cycles,cycle):
    confirm = raw_input("Are you sure (Y/n) [n]? ")
    if confirm == "Y":
        cycles.delete_cycle(cycle)
    elif confirm == "n":
        return
    else:
        return delete_cycle(cycles,cycle)
    
    
def last_n_cycles(cycles,n=None):
    
    cycle_list = cycles.to_list(reverse=True)
    
    if not n:
        print "|---------------- Cycles ----------------|"
    else:
        print "|------------- Last %d Cycles ------------|"%n
       
    print "|                      | Flow   | Cycle  |"
    print "| Cycle Start Date     | Length | Length |"
    print "|----------------------------------------|"
    i = 1
    if len(cycle_list) > 0:
        for cycle in cycle_list:
            start_dt = cycle.start_dt
            period_length = cycle.period_length
            length = cycle.length
            print "| %s | %6s | %6s |"%(start_dt.strftime("%H:00 - %b %d, %Y"),(int(round(period_length)) if period_length else '--'),(int(round(length)) if length else '--'))
            if n and i == n:
                break
            else:
                i+=1

    else:
        print "|            No cycles logged            |"
    print "|----------------------------------------|"
    return True
    
def show(cycles):
    return last_n_cycles(cycles)
    
def stats(cycles):

    if cycles.count > 0:
        average_length = cycles.avg_cycle_length
        last_start_dt = cycles.tail.start_dt
        next_start_dt = last_start_dt + timedelta(days=average_length)
        average_period_length = cycles.avg_period_length
        days_till_next_cycle = (next_start_dt - datetime.today()).days
        shortest_cycle = cycles.shortest_cycle
        longest_cycle = cycles.longest_cycle
        print ""
        print "Currently in day %d of cycle."%((datetime.today() - last_start_dt).days+1)
        if days_till_next_cycle < 0:
            print "Next cycle is %s %s late. Should have started on %s."%(abs(days_till_next_cycle),"day" if days_till_next_cycle == 1 else "days",next_start_dt.strftime('%a, %b %d'))
        else:
           print "Next cycle starts in %d day(s) on %s."%((next_start_dt - datetime.today()).days,next_start_dt.strftime('%a, %b %d'))
        print ""
        print "Average cycle length.... %s days"%round(average_length,1)
        if average_period_length != 0:
            print "Average period length... %s days"%round(average_period_length,1)
        print "Cycles logged .......... %d"%cycles.count
        if cycles.count > 1:
            print "Shortest cycle.......... %d days / %s - %s"%(round(shortest_cycle.length),shortest_cycle.start_dt.strftime('%b %d, %Y'),(shortest_cycle.next.start_dt).strftime('%b %d, %Y'))
            print "Longest cycle........... %d days / %s - %s"%(round(longest_cycle.length),longest_cycle.start_dt.strftime('%b %d, %Y'),(longest_cycle.next.start_dt).strftime('%b %d, %Y'))
    else:
        print ""
        print "  Type 'new' to add a cycle."
    return True    

def cli():

    db_dir=os.path.expanduser('~/Dropbox/Documents/')
    db_path=os.path.join(db_dir,'cycles.db')

    cycles = Cycles(db_path)

    with cycles:
        print "{Using database: %s}"%db_path
        show_cycles_after_command = True
        while True:
            if show_cycles_after_command == True:
                last_n_cycles(cycles,4)
                stats(cycles) 
            choice = display_menu()

            if choice == 'list':
                show(cycles)
                show_cycles_after_command = False
            elif choice == 'stats':
                show_cycles_after_command = True
            elif choice == 'new':
                new(cycles)
                show_cycles_after_command = True
            elif choice == 'edit':
                edit(cycles)
                show_cycles_after_command = True
            elif choice == 'help':
                show_cycles_after_command = list_commands()

            elif choice == 'quit' or choice == 'exit':
                sys.exit(0)
            else:
                show_cycles_after_command = False



if __name__ == "__main__":

    cli()

      

