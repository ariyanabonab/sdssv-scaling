# -*- coding: utf-8 -*-
"""
Created on Wed May 25 14:03:49 2022

@author: keith
"""

"""
This is a program to interactively process a list of png files and assign 
a category to each. To ensure no data is lost regular timestamped copies are saved.

The file containing the list of .pngs is a .csv file without a header. It may 
have one or two columns. The first column is the name of the png file. The second column
contains the category (if it has been allocated) 

It can either be called using a command line interface
 or as a function call. The command line accepts 1 or2 parameters
(filename and optionally path) ; if these are not
provided a dialog is initiated to select the values.

The last path used is saved in a .def file located in the users
home directory.


Prerequisites:
    This is entirely python code using standard modules that
    are included in the Anaconda distribution 

    This code has been designed to be portable and should work on
    Linux, Windows and Mac. It has been tested using Python 3.8 under
    Ubuntu 18.04 and also under Windows 10.

Coding notes
    This code is based on the QT (version QT5) widget toolkit
    (https://doc.qt.io/qtforpython/). This has been chosen rather than
    Tkinter because it is more portable and provides improved functionality
    (https://dev.to/amigosmaker/python-gui-pyqt-vs-tkinter-5hdd)
    A useful book is https://pythoncourses.gumroad.com/l/pysqtsamples



Change history

18/05/2024  JJ Hermes           Updated for non-CV and added labels
27/01/2024  Keith Inight        Initial version
02/02/2023  Keith Inight        Adjusted image size to take account of available screen

"""
import sys
from PyQt5.QtWidgets import QDialog, QApplication,  QFileDialog,QCheckBox,QGridLayout,\
        QComboBox,QPushButton,QLabel,QSpinBox,QMessageBox,QMainWindow,QVBoxLayout,\
            QHBoxLayout,QInputDialog,QSizePolicy
from PyQt5.QtCore import QCoreApplication,QDir,QRect,Qt,QSize
from PyQt5 import QtCore
from PyQt5.QtGui import QPixmap,QFont
from datetime import datetime
from pathlib import Path

import re
import os
import warnings
import pandas as pd

pd.options.mode.copy_on_write = True 

backup_interval=300 # in second
scaling=1.0 # multiplier applied to displayed image size... normally this should self-adjust and be set to 1
class MainWindow(QDialog):

    # This is the main window definition 

    def __init__(self, mylist,root_file,png_path, parent=None):
        super(MainWindow, self).__init__(parent)
        self.parent=parent
        self.mylist=mylist
        self.root_file=root_file
        self.png_path=png_path
        try:
            self.counter=self.mylist.query('category==""').iloc[0].name
        except:
            self.counter=0 # all records have been classified
        self.changed=False
        
        self.timer0=QtCore.QTimer()
        self.timer0.setInterval(backup_interval*1000)
        self.timer0.setSingleShot(False)
        self.timer0.timeout.connect(self.backup)
        self.timer0.start()
        
        myapp=QApplication.instance()
        screen = myapp.primaryScreen()
        self.available_geometry = screen.availableGeometry()

        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.png_image = QLabel()

        self.png_image.setText("")
 
        self.png_image.setObjectName("png_image")
        self.png_image.setAlignment(Qt.AlignTop)
        self.png_image.setSizePolicy(size_policy)

        self.info1=QLabel()
        #self.info1.setGeometry(0,922,40,60)
        self.info1.setObjectName("info1")
        self.info1.setFont(QFont('Arial', 18))
        
        self.info2=QLabel()
        #self.info2.setGeometry(40,922,120,60)
        self.info2.setObjectName("info2")
        self.info2.setFont(QFont('Arial', 18))
        self.info2.setAlignment(Qt.AlignLeft)
        
        self.info3=QLabel()
        #self.info3.setGeometry(160,922,900,60)
        self.info3.setObjectName("info3")
        self.info3.setFont(QFont('Arial', 10))       
        self.info3.setAlignment(Qt.AlignLeft)        
        self.plot()

        hlayout=QVBoxLayout()

        hlayout.addWidget(self.info1)
        hlayout.addWidget(self.info2)
        hlayout.addWidget(self.info3)

        layout = QHBoxLayout()

        layout.addWidget(self.png_image)
        layout.addLayout(hlayout)
      
        self.setLayout(layout)

        
    def keyPressEvent(self,event):
        if event.key()== QtCore.Qt.Key_Q:
              self.close()
        elif event.key()== QtCore.Qt.Key_D:
            self.categorise("DontKnow")
        elif event.key()== QtCore.Qt.Key_Return:  
            self.categorise("Correct")
        elif event.key()== QtCore.Qt.Key_Space:  
            self.categorise("SNRtooLow")
        elif event.key()== QtCore.Qt.Key_A:
            self.categorise("DA")
        elif event.key()== QtCore.Qt.Key_B:
            self.categorise("DB")
        elif event.key()== QtCore.Qt.Key_C:
            self.categorise("DC")
        elif event.key()== QtCore.Qt.Key_Z:
            self.categorise("DZ")
        elif event.key() == QtCore.Qt.Key_Backslash:
            self.add_comment()
        elif event.key()== QtCore.Qt.Key_G:
            self.goto()           
        elif event.key()== QtCore.Qt.Key_Left:
            if self.counter>0:
                self.counter-=1 
        elif event.key()== QtCore.Qt.Key_Right: 
            if self.counter<len(self.mylist)-1:
                self.counter+=1        
        elif event.key()== QtCore.Qt.Key_Up:   
            unclassifieds=self.mylist[self.counter:].query('category==""')
            if len(unclassifieds)>0:
                self.counter=unclassifieds.iloc[0].name         
        elif event.key()== QtCore.Qt.Key_Down: 
            unclassifieds=self.mylist[0:self.counter].query('category==""')
            if len(unclassifieds)>0:
                self.counter=unclassifieds.iloc[-1].name       
        self.plot()
        
    def closeEvent(self,event):
        self.backup()
    def plot(self):
        fname=self.mylist.loc[self.counter]['filename']
        if ".gif" not in fname:
            fname=fname+".gif"
        self.setWindowTitle("{} ".format(fname))
        try:
            pixmap=QPixmap(os.sep.join([png_path,fname]))
            aspect_ratio=pixmap.width()/pixmap.height()
            if pixmap.height()>self.available_geometry.height()*scaling:
                mod_height=int(self.available_geometry.height()*scaling)
                mod_width=int(self.available_geometry.height()*aspect_ratio*scaling)
            else:
                mod_height=int(pixmap.height()*scaling)
                mod_width=int(pixmap.width()*scaling)
            pixmap_resized = pixmap.scaled(mod_width, mod_height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.png_image.setPixmap(pixmap_resized)
            self.png_image.setFixedHeight(mod_height)
            self.png_image.setFixedWidth(mod_width)

            category=self.mylist.loc[self.counter]['category']
        except:
            category="File not found"
        self.info1.setText(str(self.counter+1)+"/"+str(len(self.mylist)))

        if category=="":
            category="Unclassified"
        self.info2.setText(category)
        
        instructions="Q\tQuit\n\n"
        if self.counter>0:
            instructions+="←\tPrevious\n↓\tPrevious\n\tunclassified\n"
        else:
            instructions+="\n\n\n"
        if self.counter<len(self.mylist)-1:
            instructions+="→\tNext\n↑\tNext\n\tunclassified\n"
        else:
            instructions+="\n\n\n"
        instructions+="\nEnter\tCorrect\nSpace\tSNR too Low\nD\tDon't know\nA\tDA\nB\tDB\nC\tDC\nZ\tDZ\n\n\\\tCustom comment\n\nG\tGo to record\n"
        #instructions+="\nC\tCV\nSpace\tNot a CV\nD\tDon't know\n\nG\tGo to record\n"
        self.info3.setText(instructions)


    def categorise(self,category):
        self.mylist.loc[self.counter,'category']=category
        unclassifieds=self.mylist[self.counter:].query('category==""')
        if len(unclassifieds)>0:
            self.counter=unclassifieds.iloc[0].name
        self.changed=True


    def backup(self):
        if self.changed==True:
            self.mylist.to_csv(os.sep.join([png_path,root_file+datetime.now().strftime("_%Y%m%d_%H%M%S.csv")]),\
                               index=False,header=False)
            self.changed=False
            print(f"Backed up {len(self.mylist)} records at "+datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))

    def add_comment(self):
        text, ok = QInputDialog.getText(self, 'Add Comment', 'Enter your comment:')
        if ok:
            current_category = self.mylist.loc[self.counter, 'category']
            if current_category:
                self.mylist.loc[self.counter, 'category'] += f" | {text}"
            else:
                self.mylist.loc[self.counter, 'category'] = text
            self.changed = True

    def goto(self):
        newrec, done2 = QInputDialog.getInt(self, 'Go to record', 'Enter record number:',1,1,len(self.mylist))
        if done2==True:
            self.counter=newrec-1

if __name__ == '__main__':

    _, appname = os.path.split(sys.argv[0])  # obtain the name of this program

    # create name of file that holds default path name
    default_file = os.sep.join([str(Path.home()), appname[:-3]+'.def'])

    if len(sys.argv) < 3:   # not got target path and filename from command line

        try:  # open file that holds default path name and file format if it exits
            f = open(default_file, 'r')
            png_path = f.readline()
            f.close()
        except:  # no existing file so set default to home directory for first run
            png_path = str(Path.home())

        # User dialog to select path and file

        file_filter = 'File of PNG names (*.csv)'   # displayed in window
        # check if thread already running - if not create one
        app = QCoreApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        # run dialog to allow user to select file for display
        response = QFileDialog.getOpenFileName(
            caption='Select .csv file',
            directory=QDir.fromNativeSeparators(png_path+os.sep),
            filter=file_filter)

        # Check if the returned data is actually a path to a file
        resp_file=QDir.toNativeSeparators(response[0])
        if os.path.isfile(resp_file) == False:
            # this should always be true but we allow for an unpredictable situation
            raise FileNotFoundError('Selected item is not a file')
        png_path, file_name = os.path.split(resp_file)

    else:  # load filename and path from command line and check if file exists
        file_name = sys.argv[1]
        if ".csv" not in file_name:
            file_name=file_name+".csv"
        if len(sys.argv) < 2: 
            png_path =""
        else:
            png_path = sys.argv[2]
        print(file_name, png_path)

        if os.path.isfile(os.sep.join([png_path, file_name])) == False:
            raise FileNotFoundError(os.sep.join([png_path, file_name]))

    # save path and format to use as defaults in next invocation
    f = open(default_file, 'w')
    f.write(png_path)
    f.close()


    mylist=pd.read_csv(os.sep.join(
        [png_path, file_name]),keep_default_na=False,na_values=[],header=None)
    print(f"{len(mylist)} records read")
    if len(mylist.columns)<2:
        mylist.columns=['filename']
        mylist['category']=''
    else:
        mylist.columns=['filename','category']
    root_file=file_name.split('.csv')[0] # remove the extension
    pattern=re.compile(r'_20\d{6,6}_') #look for a date in the file name
    
    try:
        root_file=root_file[:pattern.search(root_file).start()]  # chop off date and anything after it
    except:
        pass # no date found
    
    #root_file=root_file.split('_')[0]  

    app = QApplication([])
    proc = MainWindow(mylist,root_file,png_path)
    proc.show()
    
    app.exec()

