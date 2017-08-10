import telnetlib
import re
import tkinter
from time import sleep


timeout = 3
debugging = False
END_OF_LINE = "\n\r"
CODE_ESC = '\x1B'   # 27


class WrongOutletNumber(Exception):
    pass

cmdLogin = [
    ("User Name : ", "lab" + END_OF_LINE) ,
    ("Password  : ", "lab123" + END_OF_LINE),
    ]
cmdEnterOutletControlConfig = [
    ("<ESC>- Main Menu, <ENTER>- Refresh, <CTRL-L>- Event Log", "1" + END_OF_LINE),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", "2" + END_OF_LINE),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", "1" + END_OF_LINE),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", ),
    ]
cmdExitOutletControlConfig = [
    ("", CODE_ESC),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", CODE_ESC),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", CODE_ESC),
    ("<ESC>- Main Menu, <ENTER>- Refresh, <CTRL-L>- Event Log", "4" + END_OF_LINE),
    ]


def cmdTurnONOFFOutletN(N, command):
    if command == "ON":  # Immediate ON
        sel = "1"
    else:              # OFF
        sel = "2"
    return [
    ("", str(N) + END_OF_LINE),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", "1" + END_OF_LINE),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", sel + END_OF_LINE),
    ("Enter 'YES' to continue or <ENTER> to cancel : ", "YES" + END_OF_LINE),
    ("Press <ENTER> to continue...", END_OF_LINE),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", CODE_ESC),
    ("<ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log", CODE_ESC),
    ]


def doTelnetCommands(conn, cmdSequence):
    # set initial value mostly to suppress IDE warning
    readData = ""
    for cmd in cmdSequence:
        readData = conn.read_until(cmd[0].encode('ascii'), timeout)
        if debugging: print("Read: " + str(readData))
        try:
            conn.write(cmd[1].encode('ascii'))
            if debugging: print("Entered: " + cmd[1])
        except IndexError:
            pass                 # do nothing if no command was supplied in tuple
    # return last output for analysis
    return readData


def getONOFFstatus(host):
    """
    Returns a list of the form [ ("srxA-1", "ON"), ("srxA-2", "OFF"), ... ]
    """

    conn = telnetlib.Telnet(host)

    r = doTelnetCommands(conn, cmdLogin + cmdEnterOutletControlConfig)
    if debugging: print(r)

    regex = re.compile( "(-\s)([a-zA-Z0-9\-\s\(\)+\/]*)(ON|OFF)" )
    parsedOutletControlOutput = regex.findall( str(r) )

    if len(parsedOutletControlOutput) != NUM_OUTLETS_IN_SR:
        raise WrongOutletNumber

    res = []
    for outlet in parsedOutletControlOutput:
        res.append( (outlet[1].strip(), outlet[2]) )

    doTelnetCommands(conn, cmdExitOutletControlConfig)
    if debugging: print(str(conn.read_all() ))
    sleep(1)
    conn.close()
    sleep(1)
    return res


def turnONdevices(host, deviceNumbers):
    conn = telnetlib.Telnet(host)
    r = doTelnetCommands(conn, cmdLogin + cmdEnterOutletControlConfig)
    if debugging: print(r)
    for Ndev in deviceNumbers :
        print("Turning ON %d on %s" % (Ndev, host) )
        doTelnetCommands(conn, cmdTurnONOFFOutletN(Ndev, command="ON"))
    doTelnetCommands(conn, cmdExitOutletControlConfig)
    sleep(1)
    conn.close()
    sleep(1)


def turnOFFdevices (host, deviceNumbers):
    conn = telnetlib.Telnet(host)
    r = doTelnetCommands(conn, cmdLogin + cmdEnterOutletControlConfig)
    if debugging: print(r)
    for Ndev in deviceNumbers :
        print("Turning OFF %d on %s" % ( Ndev, host) )
        doTelnetCommands(conn, cmdTurnONOFFOutletN(Ndev, command="OFF"))
    doTelnetCommands(conn, cmdExitOutletControlConfig)
    sleep(1)
    conn.close()
    sleep(1)


def printAllSRturnedON():
    print("List of turned ON outlets: ")
    for host in devices.getSwRackList():
        print(host + " :")
        try: 
            for outlet in getONOFFstatus(host):
                if outlet[1] == "ON":
                    print(outlet[0] + outlet[1])
        except EOFError:
            print ("Connection error!")
    print("End")


def printAllSR():
    print("List of all outlets: ")
    countON = 0
    for host in devices.getSwRackList():
        print(host + " :", end="\n")
        try: 
            n = 1
            for outlet in getONOFFstatus(host) :
                print ("%d) %-25s %s" % (n, outlet[0], outlet[1]), end="\n")
                if outlet[1] == "ON": countON += 1
                n += 1
        except EOFError :
            print("Connection error!")
    print( "\nTotal ON: %d" % (countON, ) )    

COLOR_ON = "green"
COLOR_OFF = "red"
COLOR_FG_NORMAL = "black"
COLOR_FG_HIGHLIGHT_CHANGE = "cyan"


def getColorByState(state):
    if state == "ON":
        col = COLOR_ON
    else:
        col = COLOR_OFF
    return col

FILENAME_PDU_LIST = "pdu-list.txt"
NUM_OUTLETS_IN_SR = 8


class Devices (object):

    def read_SW_RACK_LIST(self):
        """
        Reads SW_RACK_LIST from file. The result should be similar to 
        ['192.168.65.220', '192.168.65.221', '192.168.65.222']
        """
        SW_RACK_LIST = []
        with open(FILENAME_PDU_LIST) as filePDUList:
            for line in filePDUList:
                SW_RACK_LIST.append(line.rstrip())
        self.__SW_RACK_LIST = SW_RACK_LIST   
    
    def getSwRackList(self):
        return self.__SW_RACK_LIST
    
    @property
    def numSwitchedRacks(self):
        return len(self.__SW_RACK_LIST)
    
    def __init__(self):
        self.read_SW_RACK_LIST() 
        self.__deviceDict = {}
        for host in self.__SW_RACK_LIST:
            listOutlets = []
            for nOutlet in range(1, NUM_OUTLETS_IN_SR+1):
                device = {"name":     "UNKNOWN",
                          "state":    "UNKNOWN",
                          "guiState": "UNKNOWN",
                          }
                listOutlets.append(device)
            self.__deviceDict[host] = listOutlets
    
    def printDevicesInfo(self):
        for hostInfo in self.__deviceDict :
            devStateList = self.__deviceDict[hostInfo]
            # dev has format ~ {'guiState': 'ON', 'name': '-AlwaysOn- TS (SRX)', 'state': 'ON'}
            for dev in devStateList :
                print( dev['name'] + " (" + dev['guiState'] + "/" + dev['state'], end = ")   ")
            print()
            
    def readActualDeviceInfoFromSRs(self):
        for host in devices.getSwRackList() :
            try:
                column = 1
                for outlet in getONOFFstatus(host) :
                    self.__deviceDict[host][column-1]["name"] = outlet[0]
                    self.__deviceDict[host][column-1]["state"] = outlet[1]
                    column += 1
            
            except EOFError :
                print ("Connection error!")
    
        # this was called copyActualDeviceInfoToGuiInfo(self)
        # now I make it part of readActualDeviceInfoFromSRs() because it is too dangerous to not run it
        for host in devices.getSwRackList():
            for column in range(1, NUM_OUTLETS_IN_SR+1) :
                self.__deviceDict[host][column-1]["guiState"] = self.__deviceDict[host][column-1]["state"]

    def getDeviceName(self, host, outletNo):
        return self.__deviceDict[host][outletNo-1]["name"]

    def getDeviceState(self, host, outletNo):
        return self.__deviceDict[host][outletNo-1]["state"]
    
    def getDeviceGuiState(self, host, outletNo):
        return self.__deviceDict[host][outletNo-1]["guiState"]
    
    def setDeviceGuiState(self, host, outletNo, newstate):
        self.__deviceDict[host][outletNo-1]["guiState"] = newstate
                    
class GuiButtons (object):
    def __init__(self):
        self.__buttons = {}
        self.initAllButtons()
        
    def initAllButtons(self):
        for host in devices.getSwRackList() :      
            for column in range(1, NUM_OUTLETS_IN_SR+1) :
                devName = devices.getDeviceName(host, column)
                buttonName = host + " " + devName
                newButton = tkinter.Button(root,  text = devName,  
                    command = lambda buttonName=buttonName, host=host, 
                        column=column : button_clicked(buttonName, host, column)
                )
                newButton.grid(row = devices.getSwRackList().index(host), column = column )
                self.__buttons[buttonName] = newButton          
        
        row = devices.numSwitchedRacks + 2
        buttonRefresh = tkinter.Button(root, text="    Refresh    ", 
                                       bg = "blue", command = button_refresh_clicked )
        buttonRefresh.grid(row = row, column = 7)
        
        buttonApply = tkinter.Button(root, text="     Apply      ", 
                                        bg = "blue", command = button_apply_clicked )
        buttonApply.grid(row=row, column = 8)
    
    def getButtons(self):
        return self.__buttons
    
    def update(self, host, number):
        buttonName = host + " " + devices.getDeviceName(host, number)
        self.__buttons[buttonName]["bg"] = getColorByState(devices.getDeviceGuiState(host,number))
        self.__buttons[buttonName]["fg"] = COLOR_FG_HIGHLIGHT_CHANGE
        
    def updateAllButtonsWithDeviceState(self):
        for host in devices.getSwRackList() :      
            for column in range(1, NUM_OUTLETS_IN_SR+1):
                buttonName = host + " " + devices.getDeviceName(host, column)
                self.__buttons[buttonName]["bg"] = getColorByState(devices.getDeviceState(host, column))
                self.__buttons[buttonName]["fg"] = COLOR_FG_NORMAL
                

def button_clicked(name, host, number) :
    print ("Clicked: " + name + " " + str(host) + " " + str(number))
    #print ("  status: %s" % (getONOFFstatus(host)[number-1] [1] , ) )
    if devices.getDeviceGuiState(host, number) == "OFF":
        devices.setDeviceGuiState(host, number, "ON")
    else:
        devices.setDeviceGuiState(host, number, "OFF")
    guiButtons.update(host, number)

def button_refresh_clicked():
    print("Refreshing...")
    devices.readActualDeviceInfoFromSRs()
    guiButtons.updateAllButtonsWithDeviceState()
    devices.printDevicesInfo()
    print("Refresh finished")

def button_apply_clicked():
    for host in devices.getSwRackList():
        devices_to_turn_ON = []
        devices_to_turn_OFF = []
        for outletNo in range(1, NUM_OUTLETS_IN_SR+1):
            ds = devices.getDeviceState(host, outletNo)
            dsGui = devices.getDeviceGuiState(host, outletNo)
            if ds != dsGui :
                if dsGui == "ON":
                    devices_to_turn_ON.append(outletNo)
                else:
                    devices_to_turn_OFF.append(outletNo)
        if devices_to_turn_ON:
            turnONdevices(host, devices_to_turn_ON)
        if devices_to_turn_OFF:
            turnOFFdevices(host, devices_to_turn_OFF)
    devices.readActualDeviceInfoFromSRs()
    guiButtons.updateAllButtonsWithDeviceState()
    devices.printDevicesInfo()
    print("Apply finished")

def runCommandCLI():
    while True:
        printAllSR()
        print("\nEnter command, e.g. '220 on 45' , 'q' for quit")
        cliInput = input(">> ").upper()
        if cliInput == "": continue
        if cliInput[0] == 'Q':
            print("Quiting.")
            break
        try :
            cliParse = reCmd.match(cliInput)
            cliParse=cliParse.groups()
            if len(cliParse) != 3:
                print ("Wrong command (len != 3).")
                continue
        except AttributeError:
            print("Wrong command (AttributeError).")
            continue        
        srIP = "192.168.65." + cliParse[0].strip()
        if srIP not in devices.getSwRackList() :
            print("Wrong IP address.\n")
            continue
        cliCommand = cliParse[1].strip().upper()
        cliOutlets = cliParse[2].strip()
        outletList = []
        for outlet in range(1, 9):
            if str(outlet) in cliOutlets :
                outletList.append(outlet)
        if cliCommand == "ON":
            print ("Turning ON outlets %s on %s" % ( str(outletList), srIP) )
            turnONdevices(srIP, outletList)
        elif cliCommand == "OFF":
            print ("Turning OFF outlets %s on %s " % ( str(outletList), srIP) )
            turnOFFdevices(srIP, outletList)
        else :
            print ("Unknown command " + cliCommand)

if __name__ == "__main__":
    print("Starting APC rack power management\n\n")
    #print("Close graphical window for text commands")
    reCmd = re.compile("([0-9]*\s*)([A-Z]+)(\s*[0-9]+)")

    print("Reading the list of switched racks from file %s ... \n" % (FILENAME_PDU_LIST, ) )
    devices = Devices()

    print("Result: ", str( devices.getSwRackList() ) )

    print("\n\nReading list of devices and building GUI window... ")
    devices.readActualDeviceInfoFromSRs()
    devices.printDevicesInfo()

    root = tkinter.Tk()              #  root is now the "main window"
    root.title("PDU rack management")

    guiButtons = GuiButtons()
    guiButtons.updateAllButtonsWithDeviceState()

    root.mainloop()

    # Uncomment for CLI
    #runCommandCLI()
