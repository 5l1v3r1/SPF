#import getopt
import argparse
import emails
import sys
import re
import os
import subprocess
import time
import signal
from collections import defaultdict
from emails import EmailTemplate
from utils import Utils
from display import Display
from gather import Gather

from modules.theharvester import theHarvester

#=================================================
# Primary CLASS
#=================================================

class Framework(object):

    def __init__(self):
        self.config = {}        # dict to contain combined list of config file options and commandline parameters
        self.email_list = []    # list of email targets
        self.webserver = None   # web server process

        # initialize some config options
        self.config["domain_name"] = ""
        self.config["company_name"] = ""
        self.config["config_filename"] = ""
        self.config["email_list_filename"] = ""

        # default all bool values to False
        self.config["verbose"] = False
        self.config["gather_emails"] = False
        self.config["enable_externals"] = False
        self.config["enable_web"] = False
        self.config["enable_email"] = False
        self.config["enable_email_sending"] = False
        self.config["simulate_email_sending"] = False
        self.config["daemon_web"] = False
        self.config["always_yes"] = False


        # get current IP
        self.config['ip'] = Utils.getIP()

        # set a few misc values
        self.pid_path = os.path.dirname(os.path.realpath(__file__)) + "/../"
        self.display = Display()
        self.email_templates = defaultdict(list)

    #==================================================
    # SUPPORT METHODS
    #==================================================

    def cleanup(self):
        self.display.alert("Ctrl-C caught!!!")
        if (self.webserver is not None):
            if (self.config["daemon_web"]):
                self.display.alert("Webserver is still running as requested.")
            else:
                # send SIGTERM to the web process
                self.display.output("stopping webserver")
                self.webserver.send_signal(signal.SIGINT)
                # delete the pid file
                os.remove(self.pid_path + "spfwebsrv.pid") 
        # call report generation
        self.generateReport()
        # exit
        sys.exit(0)

    def generateReport(self):
        self.display.output("Generating phishing report")
        self.display.log("ENDTIME=%s\n" % (time.strftime("%Y/%m/%d %H:%M:%S")), filename="INFO.txt")

        path = os.path.dirname(os.path.realpath(__file__))
        # Start process
        cmd = [path + "/../report.py", os.getcwd() + "/" + self.config["domain_name"] + "_" + self.config["phishing_domain"] + "/"]
        self.display.output("Report file located at %s%s" % (os.getcwd() + "/" + self.config["domain_name"] + "_" + self.config["phishing_domain"] + "/", subprocess.check_output(cmd)))

    def parse_parameters(self, argv):
        parser = argparse.ArgumentParser()

        #==================================================
        # Required Args
        #==================================================
#        requiredgroup = parser.add_argument_group('required arguments')
#        requiredgroup.add_argument("-d",
#                            metavar="<domain>",
#                            dest="domain",
#                            action='store',
#                            required=True,
#                            help="domain name to phish")

        #==================================================
        # Input Files
        #==================================================
        filesgroup = parser.add_argument_group('input files')
        filesgroup.add_argument("-f",
                            metavar="<list.txt>",
                            dest="email_list_file",
                            action='store',
#                            type=argparse.FileType('r'),
                            help="file containing list of email addresses")
        filesgroup.add_argument("-C",
                            metavar="<config.txt>",
                            dest="config_file",
                            action='store',
#                            type=argparse.FileType('r'),
                            help="config file")

        #==================================================
        # Enable Flags
        #==================================================
        enablegroup = parser.add_argument_group('enable flags')
        enablegroup.add_argument("--all",
                            dest="enable_all",
                            action='store_true',
                            help="enable ALL flags... same as (-e -g -s -w)")
        enablegroup.add_argument("--test",
                            dest="enable_test",
                            action='store_true',
                            help="enable all flags EXCEPT sending of emails... same as (-e -g --simulate -w -y -v -v)")
        enablegroup.add_argument("-e",
                            dest="enable_external",
                            action='store_true',
                            help="enable external tool utilization")
        enablegroup.add_argument("-g",
                            dest="enable_gather_email",
                            action='store_true',
                            help="enable automated gathering of email targets")
        enablegroup.add_argument("-s",
                            dest="enable_send_email",
                            action='store_true',
                            help="enable automated sending of phishing emails to targets")
        enablegroup.add_argument("--simulate",
                            dest="simulate_send_email",
                            action='store_true',
                            help="simulate the sending of phishing emails to targets")
        enablegroup.add_argument("-w",
                            dest="enable_web",
                            action='store_true',
                            help="enable generation of phishing web sites")
        enablegroup.add_argument("-W",
                            dest="daemon_web",
                            action='store_true',
                            help="leave web server running after termination of spf.py")

        #==================================================
        # Optional Args
        #==================================================
        parser.add_argument("-d",
                            metavar="<domain>",
                            dest="domain",
                            action='store',
                            help="domain name to phish")
        parser.add_argument("-c",
                            metavar="<company's name>",
                            dest="company",
                            action='store',
                            help="name of company to phish")
        parser.add_argument("--ip",
                            metavar="<IP address>",
                            dest="ip",
                            default=Utils.getIP(),
                            action='store',
                            help="IP of webserver defaults to [%s]" % (Utils.getIP()))
        parser.add_argument("-v", "--verbosity",
                            dest="verbose",
                            action='count',
                            help="increase output verbosity")

        #==================================================
        # Misc Flags
        #==================================================
        miscgroup = parser.add_argument_group('misc')
        miscgroup.add_argument("-y",
                            dest="always_yes",
                            action='store_true',
                            help="automatically answer yes to all questions")

        args = parser.parse_args()

        # convert parameters to values in the config dict
        self.config["domain_name"] = args.domain
        if (self.config["domain_name"] is None):
            self.config["domain_name"] = ""
        self.config["company_name"] = args.company
        self.config["ip"] = args.ip
        self.config["config_filename"] = args.config_file
        self.config["email_list_filename"] = args.email_list_file
        self.config["verbose"] = args.verbose
        self.config["gather_emails"] = args.enable_gather_email
        self.config["enable_externals"] = args.enable_external
        self.config["enable_web"] = args.enable_web
        self.config["enable_email_sending"] = args.enable_send_email
        self.config["simulate_email_sending"] = args.simulate_send_email
        self.config["daemon_web"] = args.daemon_web
        self.config["always_yes"] = args.always_yes

        if (args.enable_all == True):
            self.config["gather_emails"] =  True
            self.config["enable_externals"] = True
            self.config["enable_web"] = True
            self.config["enable_email_sending"] = True

        if (args.enable_test == True):
            self.config["gather_emails"] = True
            self.config["enable_externals"] = True
            self.config["simulate_email_sending"] = True
            self.config["enable_web"] = True
            self.config["always_yes"] = True
            self.config["verbose"] = 2

        good = True
        if (not good):
            self.display.error("Please enable/define at least one of the following parameters: --all --test -e -g -s --simulate -w")
            print
            parser.print_help()
            sys.exit(1)


    #==================================================
    # Primary METHOD
    #==================================================

    def run(self, argv):

        #==================================================
        # Process/Load commanline args and config file
        #==================================================

        self.parse_parameters(argv)

        # load the config file
        if (self.config["config_filename"] is not None):
            temp1 = self.config
            temp2 = Utils.load_config(self.config["config_filename"])
            self.config = dict(temp2.items() + temp1.items())
        else:
            if Utils.is_readable("default.cfg"):
                self.display.error("a CONFIG FILE was not specified...  defaulting to [default.cfg]")
                print
                temp1 = self.config
                temp2 = Utils.load_config("default.cfg")
                self.config = dict(temp2.items() + temp1.items())
            else:
                self.display.error("a CONFIG FILE was not specified...")
                print
                sys.exit()

        # set verbosity level
        if (self.config['verbose'] >= 1):
            self.display.enableVerbose()
        if (self.config['verbose'] > 1):
            self.display.enableDebug()

        # set logging path
        self.display.setLogPath(os.getcwd() + "/" + self.config["domain_name"] + "_" + self.config["phishing_domain"] + "/")

        self.display.log("STARTTIME=%s\n" % (time.strftime("%Y/%m/%d %H:%M:%S")), filename="INFO.txt")
        self.display.log("TARGETDOMAIN=%s\n" % (self.config["domain_name"]), filename="INFO.txt")
        self.display.log("PHISHINGDOMAIN=%s\n" % (self.config["phishing_domain"]), filename="INFO.txt")
        #==================================================
        # Load/Gather target email addresses
        #==================================================

        if ((self.config["email_list_filename"] is not None) or (self.config["gather_emails"] == True)):
            print
            self.display.output("Obtaining list of email targets")
            if (self.config["always_yes"] or self.display.yn("Continue", default="y")):

                # if an external emaillist file was specified, read it in
                if self.config["email_list_filename"] is not None:
                    file = open(self.config["email_list_filename"], 'r')
                    temp_list = file.read().splitlines()
                    self.display.verbose("Loaded [%s] email addresses from [%s]" % (len(temp_list), self.config["email_list_filename"]))
                    self.email_list += temp_list
            
                # gather email addresses
                if self.config["gather_emails"] == True:
                    if (self.config["domain_name"] == ""):
                        self.display.error("No target domain specified.  Can not gather email addresses.")
                    else:
                        self.display.verbose("Gathering emails via built-in methods")
                        self.display.verbose(Gather.get_sources())
                        self.gather = Gather(self.config["domain_name"], display=self.display)
                        temp_list = self.gather.emails()
                        self.display.verbose("Gathered [%s] email addresses from the Internet" % (len(temp_list)))
                        self.email_list += temp_list
                        print
    
                        # gather email addresses from external sources
                        if (self.config["gather_emails"] == True) and (self.config["enable_externals"] == True):
                            # theHarvester
                            self.display.verbose("Gathering emails via theHarvester")
                            thr = theHarvester(self.config["domain_name"], self.config["theharvester_path"], display=self.display)
                            out = thr.run()
                            if (not out):
                                temp_list = thr.emails()
                                self.display.verbose("Gathered [%s] email addresses from theHarvester" % (len(temp_list)))
                                self.email_list += temp_list
                            else:
                                self.display.error(out)
                            print
    
    #                        # Recon-NG
    #                        self.display.verbose("Gathering emails via Recon-NG")
    #                        temp_list = reconng(self.config["domain_name"], self.config["reconng_path"]).gather()
    #                        self.display.verbose("Gathered [%s] email addresses from Recon-NG" % (len(temp_list)))
    #                        self.email_list += temp_list
            
                # sort/unique email list
                self.email_list = Utils.unique_list(self.email_list)
                self.email_list.sort()
            
                # print list of email addresses
                self.display.verbose("Collected [%s] unique email addresses" % (len(self.email_list)))
                self.display.print_list("EMAIL LIST",self.email_list)
                for email in self.email_list:
                    self.display.log(email + "\n", filename="email_targets.txt")

        #==================================================
        # Load web sites
        #==================================================

        if self.config["enable_web"] == True:
            print
            self.display.output("Starting phishing webserver")
            if (self.config["always_yes"] or self.display.yn("Continue", default="y")):

                path = os.path.dirname(os.path.realpath(__file__))
                # Start process
                cmd = [path + "/../web.py", Utils.compressDict(self.config)]
                self.webserver = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE)
    
                # monitor output to gather website information
                while True:
                    line = self.webserver.stdout.readline()
                    line = line.strip()
                    if line == 'Websites loaded and launched.':
                        break
                    if line != '':
                        self.display.verbose(line)
                        match=re.search("Started website", line)
                        VHOST = ""
                        PORT = ""
                        if match:
                            parts=line.split("[")
                            VHOST=parts[1].split("]")
                            VHOST=VHOST[0].strip()
                            PORT=parts[2].split("]")
                            PORT=PORT[0].strip()
                            PORT=PORT[7:]
                            # keep the URL clean
                            # if port is 80, then it does not need to be included in the URL
                            if (PORT[-3:] == ":80"):
                                PORT = PORT[:-3]
    
                            self.config[VHOST + "_port"] = PORT
                            self.config[VHOST + "_vhost"] = VHOST
                            Utils.screenCaptureWebSite("http://" + PORT,
                                os.getcwd() + "/" +
                                self.config["domain_name"] + "_" + self.config["phishing_domain"] + "/" +
                                PORT + "_" + VHOST + ".png")
                            Utils.screenCaptureWebSite("http://" + VHOST + "." + self.config["phishing_domain"],
                                os.getcwd() + "/" +
                                self.config["domain_name"] + "_" + self.config["phishing_domain"] + "/" +
                                VHOST + "." + self.config["phishing_domain"] + ".png")
    
                # Write PID file
                pidfilename = os.path.join(self.pid_path, "spfwebsrv.pid")
                pidfile = open(pidfilename, 'w')
                pidfile.write(str(self.webserver.pid))
                pidfile.close()
                self.display.verbose("Started WebServer with pid = [%s]" % self.webserver.pid)

        #==================================================
        # Build array of email templates
        #==================================================

        if (((self.email_list is not None) and (self.email_list)) and ((self.config["enable_email_sending"] == True) or (self.config["simulate_email_sending"] == True))):
            print
            self.display.verbose("Locating phishing email templates")
            if (self.config["always_yes"] or self.display.yn("Continue", default="y")):

                # loop over each email template
                for f in os.listdir("templates/email/"):
                    template_file = os.path.join("templates/email/", f)
                    self.display.debug("Found the following email template: [%s]" % template_file)
            
                    if ((Utils.is_readable(template_file)) and (os.path.isfile(template_file))):
                        # read in the template SUBJECT, TYPE, and BODY
                        TYPE = ""
                        SUBJECT = ""
                        BODY = ""
                        with open (template_file, "r") as myfile:
                            for line in myfile.readlines():
                                match=re.search("TYPE=", line)
                                if match:
                                    TYPE=line.replace('"', "")
                                    TYPE=TYPE.split("=")
                                    TYPE=TYPE[1].lower().strip()
                                match2=re.search("SUBJECT=", line)
                                if match2:
                                    SUBJECT=line.replace('"', "")
                                    SUBJECT=SUBJECT.split("=")
                                    SUBJECT=SUBJECT[1].strip()
                                match3=re.search("BODY=", line)
                                if match3:
                                    BODY=line.replace('"', "")
                                    BODY=BODY.replace(r'\n', "\n")
                                    BODY=BODY.split("=")
                                    BODY=BODY[1].strip()
                        self.email_templates[TYPE].append(EmailTemplate(TYPE, SUBJECT, BODY))
        
        #==================================================
        # Generate/Send phishing emails
        #==================================================

        if ((self.config["enable_email_sending"] == True) or (self.config["simulate_email_sending"] == True)):
            if ((self.config["determine_smtp"] == "1") and (self.config["use_specific_smtp"] == "1")):
               self.display.error("ONLY 1 of DETERMINE_SMTP or USE_SPECIFIC_SMTP can be enabled at a time.")
            else:
                print
                self.display.output("Sending phishing emails")
                if (self.config["always_yes"] or self.display.yn("Continue", default="y")):

                    templates_logged = []
                    #do we have any emails top send?
                    if self.email_list:
                        temp_target_list = self.email_list
                        temp_delay = 1
                        if (self.config["email_delay"] is not None):
                            temp_delay = int(self.config["email_delay"])
                        send_count = 0
                        # while there are still target email address, loop
                        while (temp_target_list and (send_count < (int(self.config["emails_max"])))):
                            # inc number of emails we have attempted to send
                            send_count = send_count + 1
                            # delay requested amount of time between sending emails
                            time.sleep(temp_delay)
                            # for each type of email (citrix, owa, office365, ...)
                            for key in self.email_templates:
                                # double check
                                if temp_target_list:
                                    # for each email template of the given type
                                    for template in self.email_templates[key]:
                                        # double check
                                        if temp_target_list:
                                            # grab a new target email address
                                            target = temp_target_list.pop(0)
                                            self.display.verbose("Sending Email to [%s]" % target)
                                            #FROM = "support@" + self.config["phishing_domain"]
                                            FROM = self.config["smtp_fromaddr"]
        
                                            SUBJECT = template.getSUBJECT()
                                            BODY = template.getBODY()
        
                                            # perform necessary SEARCH/REPLACE 
                                            if self.config["enable_host_based_vhosts"] == "1":
                                                BODY=BODY.replace(r'[[TARGET]]', "http://" + key + "." + self.config["phishing_domain"])
                                                if self.config["default_web_port"] != "80":
                                                    BODY += ":" + self.config["default_web_port"]
                                            else:
                                                BODY=BODY.replace(r'[[TARGET]]', "http://" + self.config[key + "_port"])
    
                                            # log
                                            if (key not in templates_logged):
                                                self.display.log("----------------------------------------------\n\n" +
                                                                 "TO: <XXXXX>\n" +
                                                                 "FROM: " + FROM + "\n" +
                                                                 "SUBJECT: " + SUBJECT + "\n\n" +
                                                                 BODY + "\n\n" + 
                                                                 "----------------------------------------------\n\n" +
                                                                 "TARGETS:\n" +
                                                                 "--------\n",
                                                                 filename="email_template_" + key + ".txt")
                                                templates_logged.append(key)
                                            self.display.log(target + "\n", filename="email_template_" + key + ".txt")
                                            
                                            # send the email
                                            if (self.config["simulate_email_sending"] == True):
                                                self.display.output("Would have sent an email to [%s] with subject of [%s], but this was just a test." % (target, SUBJECT))
                                            else:
                                                try:
                                                    if self.config["determine_smtp"] == "1":
                                                        emails.send_email_direct(target, FROM, SUBJECT, BODY, debug=True)
                                                    if self.config["use_specific_smtp"] == "1":
                                                        #self.display.error("[USE_SPECIFIC_SMTP] not implemented")
                                                        print self.config["smtp_fromaddr"]
                                                        emails.send_email_account(self.config["smtp_server"], int(self.config["smtp_port"]), self.config["smtp_user"], self.config["smtp_pass"], target, self.config["smtp_fromaddr"], SUBJECT, BODY, debug=True)
                                                except:
                                                    self.display.error(sys.exc_info()[0])


        #==================================================
        # Monitor web sites
        #==================================================

        if self.config["enable_web"] == True:
            print
            self.display.output("Monitoring phishing website activity!")
            self.display.alert("(Press CTRL-C to stop collection and generate report!)")
            if (self.webserver):
                while True:
                    line = self.webserver.stdout.readline()
                    line = line.strip()
                    self.display.output(line)
