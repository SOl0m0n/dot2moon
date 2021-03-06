#!/usr/bin/python
#coding: utf-8

__AUTHOR__ = "Fnkoc"
__LICENSE__= "MIT"

"""
MIT License

Copyright (c) 2017 Franco Colombino

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from threading import Thread, active_count
from sys import path, argv
from colorama import Fore
from time import sleep
from re import sub
path.append("src")
import useragents
import connection
import threading
import argparse
import results
import banner
import tester

parser = argparse.ArgumentParser(
        description = "Path Traversal tester and validator",
        add_help = True)
parser.add_argument(
        "-u", 
        required = True,
        help = "Target site")
parser.add_argument(
        "-w",
        required = True,
        help = "Wordlist used to test")
parser.add_argument(
        "-v", 
        action = "store_true",
        help = "Verbose, details every step")
parser.add_argument(
        "-t",
        type = int,
        default = 4,
        help = "Number of threads that will be executed (default = 4)")
parser.add_argument(
        "-p",
        help = "POST explotation. Inform parameter")
parser.add_argument(
        "-o", 
        help = "Save results to file")
parser.add_argument(
        "-c",
        type = int,
        default = 300,
        help = "Define how many characters of HTML will be shown")
parser.add_argument(
        "--user-agent", 
        dest = "UserAgent",
        help = "Change requests User-Agent")
parser.add_argument(
        "--ignore",
        help = "Look for specific string in HTML. If found, discart page")
parser.add_argument(
        "--timeout",
        type = float,
        default = 10,
        help = "Set timeout")
parser.add_argument(
        "--random-agent",
        action = "store_true",
        dest ="RandomAgent",
        help = "Set random user agent")
parser.add_argument(
        "--timeset",
        type = float,
        default = None,
        help = "Set time between requests")

args = parser.parse_args()

def check():
    """
	Check All Requirements (URL, Server Status, Redirect
    """
    if args.RandomAgent == True:
        args.UserAgent = useragents.generate()

    conn = connection.verify(
    	args.u, args.v, args.UserAgent, args.timeout)

    #Validates input URL
    conn.url()
    
    #Returns url and HTTP code
    code = conn.HTTPcode(True)

    if code[1] == 200:
        print(" [+] Server Status: Online")
        print(" [+] Response code: ", code[1])
    else:
        print(" [-] Server Status: Offline")
        print("Response code: ", code[1])
        follow = input(" [!] Proceed anyway? [y/n] ")

        if follow == "n":
            exit()
        else:
            #returns URL, default page size, default html
            return(args.u, 0, "not found")
   
    #Get default failed injection page size
    #Returns URL and Default page size
    default_p_size = conn.PageSize(True)
    
    #Get default page HTML
    default_html = conn.HTML(True)
    default_html = sub("<.*?>","",default_html)
    
    #Check for redirect (True)
    target_url = conn.redirect(True, True)

    #Returns URL, (URL, default page size), default_html
    if args.p != None:
        par = conn.parameter(args.p)
        return(target_url, default_p_size, default_html, par)
    else:
        return(target_url, default_p_size, default_html)

def wordlist():
    """
        Opens Wordlist File and read it
    """
    with open(args.w, "r") as wl:
        wl = wl.readlines()
    return(wl)

def test_POST(target_info, wlist):
    """
        [POST] Path test function
    """
    #target_info is a tuple and has
    # [0] = URL
    # [1] = default page size
    # [2] = default HTML page
    # [3] = injection parameter
    target = target_info[0]
    p_size_default = target_info[1]
    p_html_default = target_info[2]
    parameter = target_info[3]

    #Will go through all the lines in the wordlist
    for directory in wlist:
        directory = directory.rstrip()
        
        if directory not in scanned:
            scanned.append(directory)
            #If --timeset in use. The program will wait before next request
            if args.timeset != None:
                if args.v == True:
                    print("sleeping %s seconds" % args.timeset)
                sleep(args.timeset)
            
            for p in parameter:
                #First run has "PAYLOAD" as value
                if parameter[p] == "PAYLOAD":
                    parameter[p] = directory
                #After the first, it adquires the injection payload value
                elif "/" in parameter[p]:
                    parameter[p] = directory

            conn = connection.verify(
                    target, args.v, args.UserAgent, args.timeout)
            post_response = conn.post(directory, parameter)

            infos[post_response[3]] = [post_response[1]]

            html = sub("<.*?>","",post_response[2])
            teste_html = tester.crawler(html, args.v)
            comparation = teste_html.compare(p_html_default)
            if comparation == "not_equal":
                teste_string = teste_html.strings(args.ignore)

                if teste_string == "not_found":
                    infos[post_response[3]].append(html)
        else:
            pass


def test_GET(target_info, wlist):
    """
        [GET] Path test function
    """
    #target_info is a tuple and has
    # [0] = URL
    # [1] = default page size
    # [2] = default HTML page
    target = target_info[0]
    p_size_default = target_info[1]
    p_html_default = target_info[2]

    #Will go through all the lines in the wordlist
    for directory in wlist:
        directory = directory.rstrip()

        if directory not in scanned:
            scanned.append(directory)
            #If --timeset in use. The program will wait before next 
            #request        
            if args.timeset != None:
                if args.v == True:
                    print("sleeping %s seconds" % args.timeset)
                sleep(args.timeset)
            
            #Here the final URL will be treated. This way we can assure the
            #Right URL and payload will be passed
            #Check if target URL finishs with "/"
            # site.com/index.php?file=     ../etc/passwd
            if directory[0] != "/":
                if target[-1] != "/":
                    #Final target becomes
                    #site.com/index.php?file=../etc/passwd
                    final_target = target + directory
                #If site.com/index.php?file=/  ../etc/passwd
                else:
                    #Final target becomes
                    #site.com/index.php?file=../etc/passwd
                    final_target = target[:-1] + directory
            # site.com/index.php?file=     /../etc/passwd
            else:
                #Final target becomes
                #site.com/index.php?file=../etc/passwd
                final_target = target + directory[1:]

            if args.RandomAgent == True:
                args.UserAgent = useragents.generate()

            conn = connection.verify(
                    final_target, args.v, args.UserAgent, args.timeout)
            #Checks for HTTP code of URL + payload. False to "check"
            #Response_code returns (URL tested, HTTP code)
            response_code = conn.HTTPcode(False)

            #If page exists, check for redirections
            if response_code[1] == 200:
                #Add HTTP code results to found list
                infos[response_code[0]] = [response_code[1]]               

                #Returns URL and Page size. Gives False to "check"
                p_size = conn.PageSize(False)
                #Add page size results to size list
                infos[p_size[0]].append(p_size[1])
                
                #Returns (URL, serverURL, Redirect status)
                #False both to "check" and "parameter" Parameter will only 
                #be relevant if checking.
                verify_red = conn.redirect(False, False)
                #Add redirect results to redirect list
                infos[verify_red[0]].append(verify_red[1]) #server URL
                infos[verify_red[0]].append(verify_red[2]) #Redirect status

                #Downloads page source code
                #Returns page HTML. False to "check"
                html = conn.HTML(False)

                html = sub("<.*?>","",html)
                
                #Calls module tha test source code content
                test_html = tester.crawler(html, args.v)

                #Test HTML if it's the same as default page                
                comparation = test_html.compare(p_html_default)
                if comparation == "not_equal":
                    #IF passes in first test. Go further

                    #Test HTML if contain payload string inside of HTML
                    test_payload = test_html.payload(final_target)
                    if test_payload[2] == "not_found":
                        #If passes on second test. Go further
                    
                        #Test HTML if contain specific strings
                        test_string = test_html.strings(args.ignore)
                        if test_string == "not_found":
                            #If passes on third test. Go further
                        
                            #Compares pages byte size
                            if p_size != p_size_default:
                                #Potential result
                                infos[final_target].append(html)

        #If yes directory in scanned, skip
        else:
            pass

if __name__ == "__main__":
    #Declares global variable that will be used to store all scanned paths and
    #its informations
    global scanned
    scanned = []
    global infos
    infos = {}

    #Inform that the program is starting
    print(" [+] The program has been initiated")

    #If --timeset is used, only one thread will be available
    if args.timeset != None:
        args.t = 1
        print(" [!] --timeset in use. Running single thread")

    #Inform number of threads that will be created
    print(" [+] Using %s workers" % args.t)

    #Inform timeout
    print(" [+] Timeout set of %.2f seconds" % args.timeout)
    
    #Calls Check function in order to check requirements
    #Target now returns URL, default page size, default html
    target = check()
    
    #Calls function to retrieve wordlist
    #w_list returns Wordlist content
    w_list = wordlist()

    #start Threads
    print(" [+] Starting Tests...")
    count_t = 0
    for i in range(args.t):
        if args.v == True:
            count_t += 1
            print(" [+] Starting Thread %i" % count_t)

        if args.p:
            threading.Thread(target = test_POST, args = (target, w_list,)).start()
        else:
            #Must have comma after w_list, so it will not try to unpack the list
            threading.Thread(target = test_GET, args = (target, w_list,)).start()
            #Waits 1 second before starting another thread
        sleep(1)
    
    #Loop
    loop = True    
    while loop == True:
        #Waits until all other workers have stopped
        if active_count() == 1:
            loop = False

            #Just to divide the screen
            print(Fore.GREEN)
            print("-"*80)
            print("-"*20+"RESULTS"+("-"*53))
            print("-"*80)
            print(Fore.RESET)

            #Check if infos contains any information
            if len(infos) != 0:
                #Call module to print all results.
                #target[1][1] = default page size
                rst = results.show(infos, target[1][1], args.p)
                #Retrive Average Page Size
                avg = rst.AverageSize()
                #Print All Results Information
                rst.detail(avg, args.c)
                #Print only Potential results
                rst.potential(avg, args.c, target[2])
                if args.o != None:
                    rst.output(args.o, avg)
            else:
                print(" [-] Unfortunately the tests had no positive results")
                print(" [-] Quitting...")
