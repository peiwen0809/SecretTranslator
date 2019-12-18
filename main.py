import sys
from gui import Ui_MainWindow  # 匯入GUI

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtGui import QPainter, QColor, QPen, QDrag, QFont, QImage, QPainterPath
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QTextEdit, QUndoStack, QUndoCommand
from PyQt5.QtCore import Qt, QPoint, QRect, QMimeData
from sklearn import cluster,metrics
import os
import io
import copy
import cv2
import numpy as np
from google.cloud import vision
from google.cloud.vision import types
from google.cloud import translate
from os.path import expanduser
import matplotlib.pyplot as plt

class textedit1(QTextEdit):
    def __init__(self, parent):
        super().__init__(parent)

    #移動textedit
    def mouseMoveEvent(self, e):
        if e.buttons() != Qt.RightButton:
            return
        print("dragdag")
        print(e.x(), e.y())

        mimeData = QMimeData()
        mimeData.setText('%d,%d' % (e.x(), e.y()))
        print("dragdag")

        pixmap = QLabel.grab(self)
        # below makes the pixmap half transparent
        painter = QPainter(pixmap)
        painter.setCompositionMode(painter.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 127))
        painter.end()

        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(pixmap)
        drag.setHotSpot(e.pos() - self.rect().topLeft())
        dropAction = drag.exec_(Qt.MoveAction)


class mylabel(QLabel):
    print("into mylabel")
    def __init__(self, parent):
        super(mylabel, self).__init__(parent)
        self.image = QImage()
        self.drawing = True
        self.lastPoint = QPoint()
        self.modified = False
        self.scribbling = False
        self.eraserSize = 5  #橡皮擦初始值
        self.fontSize = 12   #字形初始值
        self.setAcceptDrops(True)
        self.savetextedit = []
        self.text = [] #紀錄文字
        self.eraserPos = []
        self.temp_img = 1   #紀錄圖片編號
        self.numstack = []

        self.i = 0  # 紀錄textedit

        self.eraserClicked = False
        self.textClicked = False
        self.clearClicked = False

        self.undoStack = QUndoStack()
        self.m_undoaction = self.undoStack.createUndoAction(self, self.tr("&Undo"))
        # self.m_undoaction.setShortcut('Ctrl+Z')
        self.addAction(self.m_undoaction)
        self.m_redoaction = self.undoStack.createRedoAction(self, self.tr("&Redo"))
        # self.m_redoaction.setShortcut('Ctrl+Y')
        self.addAction(self.m_redoaction)

    #開啟圖片
    def openimage(self, filename):
        self.image = filename
        self.scaredPixmap = self.image.scaled(self.width(), self.height(), aspectRatioMode=Qt.KeepAspectRatio)
        self.image = self.scaredPixmap
        self.setAlignment(Qt.AlignLeft)
        self.update()

    #獲得橡皮擦大小
    def getErasersize(self, esize):
        self.eraserSize = int(esize)
        print(self.eraserSize)
    #獲得字體大小
    def getFontsize(self, fsize):
        self.fontSize = int(fsize)
        print(self.fontSize)

    def mousePressEvent(self, event):
        print("left press")
        super().mousePressEvent(event)

        if event.button() == Qt.LeftButton and self.eraserClicked:
            print("start erase action")
            self.drawing = True
            self.eraserPos.clear()
            self.lastPoint = event.pos()
            self.eraserPos.append(self.lastPoint)


        elif event.button() == Qt.LeftButton and self.textClicked:
            print("add textedit")
            self.item = self.childAt(event.x(), event.y())
            if not self.childAt(event.x(), event.y()):  # 如果不是點在文字框上的話
                # 文字框
                self.textedit = textedit1(self)
                self.textedit.setObjectName("textedit{}".format(self.i))
                self.textedit.setStyleSheet("background-color:rgb(255,255,255,0);\n"  # 設定透明度
                                            "border: 6px solid black;\n");  # 設定邊框
                self.textedit.move(event.pos().x(), event.pos().y())

                self.savetextedit.append(self.textedit)
                print("record textedit", self.savetextedit)

                # 設定文字框格式
                self.textedit.setFont(QFont("Roman times", self.fontSize))
                self.textedit.setLineWrapMode(QTextEdit.FixedColumnWidth)  # 自動斷行
                self.textedit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隱藏滾動軸
                self.textedit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隱藏滾動軸

                self.textedit.show()
                print(self.textedit)

                self.item = self.childAt(event.x(), event.y())
                print("choose item", self.item)

                command = storeCommand(self.textedit)
                self.undoStack.push(command)
                print("undostack count", self.undoStack.count())
                print("into undostack", self.textedit)

                if self.textedit:  # 將文字框設為不能寫
                    x = 0
                    for self.savetextedit[x] in self.savetextedit:
                        self.savetextedit[x].setReadOnly(True)
                        self.savetextedit[x].setStyleSheet("background-color:rgb(255,255,255,0);\n"  # 設定透明度
                                                           "border: 6px solid black;\n");  # 設定邊框
                        x = x + 1

            else:
                self.item.setReadOnly(False)
                self.doc = self.item.document()
                self.doc.contentsChanged.connect(self.textAreaChanged)  # 隨著輸入的文字改變文字框的大小

        elif event.button() == Qt.RightButton:
            self.item = self.childAt(event.x(), event.y())
            print("choose textedit", self.item)

            # 有存到stack裡，可是沒辦法redo，沒辦法傳進去移動過後的位置
            try:
                if self.item:
                    self.item.setReadOnly(True)
                    print("moveCmd", self.item, self.item.pos())
                    # self.undoStack.push(moveCommand(self.item, self.item.pos()))
                    self.undoStack.push(moveCommand(self.item, self.item.pos()))
                    print("moveundostack count", self.undoStack.count())
            except Exception as e:
                print(e)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            print("delete textedit", self.item)
            self.item.deleteLater()
            self.savetextedit.remove(self.item)

    # 隨著輸入的文字改變文字框大小
    def textAreaChanged(self):
        self.doc.adjustSize()
        newWidth = self.doc.size().width() + 20
        newHeight = self.doc.size().height() + 20
        if newWidth != self.item.width():
            self.item.setFixedWidth(newWidth)
        if newHeight != self.item.height():
            self.item.setFixedHeight(newHeight)

    def dragEnterEvent(self, e):
        print("drag")
        e.accept()

    def dropEvent(self, e):
        print("drop item")
        mime = e.mimeData().text()
        x, y = map(int, mime.split(','))
        print(x,y)
        position = e.pos()
        print(position)

        e.source().setReadOnly(True)
        self.undoStack.push(moveCommand(e.source(), e.source().pos()))

        e.source().move(position - QPoint(x,y))
        print("move item to", self.item.pos())
        e.setDropAction(Qt.MoveAction)
        e.accept()

    def mouseMoveEvent(self, event):
        if (event.buttons() and Qt.LeftButton) and self.drawing and self.eraserClicked:
            print("start painting")
            self.path = QPainterPath()
            self.path.moveTo(self.lastPoint)
            self.path.lineTo(event.pos())

            painter = QPainter(self.image)
            x = self.width() - self.image.width()
            y = self.height() - self.image.height()
            painter.translate(x / 2 - x, y / 2 - y)  #因為將圖片置中，所以要重設置畫筆原點
            painter.setPen(QPen(Qt.white, self.eraserSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(self.path)
            print(self.path)

            self.lastPoint = event.pos()
            self.eraserPos.append(self.lastPoint)
            self.update()

    def mouseReleaseEvent(self, event):
        print("release mouse")
        if event.button() == Qt.LeftButton:
            self.drawing = False

            #儲存圖片佔存，供undo redo使用
            if self.eraserClicked == True:
                self.imagename = "img{}.PNG".format(self.temp_img)
                print(self.imagename)
                self.image.save("./saveload/{}".format(self.imagename))
                self.temp_img = self.temp_img + 1
                self.numstack.append(self.imagename)

    def paintEvent(self, event):
        canvasPainter = QPainter(self)
        self.x = (self.width() - self.image.width())/2
        self.y = (self.height() - self.image.height())/2
        canvasPainter.translate(self.x, self.y)
        canvasPainter.drawImage(event.rect(), self.image, event.rect())

        if not self.textClicked:
            x = 0
            self.undoStack.clear()
            for self.savetextedit[x] in self.savetextedit:
                self.savetextedit[x].setStyleSheet("background-color:rgb(255,255,255,0);\n"  # 設定透明度
                                        "border: 6px solid transparent;\n");  # 設定邊框
                if self.savetextedit[x].toPlainText() == "":
                    self.savetextedit[x].deleteLater()
                    self.savetextedit.remove(self.savetextedit[x])
                x = x + 1

        self.update()

#新增textedit的undo redo command
class storeCommand(QUndoCommand):
    def __init__(self, textedit):
        QUndoCommand.__init__(self)
        self.item1 = textedit
        print("storecommand", self.item1)

    def undo(self):
        print("undo textedit", self.item1)
        self.item1.hide()

    def redo(self):
        self.item1.show()

#移動textedit的undo redo command
class moveCommand(QUndoCommand):
    def __init__(self, textedit2, pos):
        QUndoCommand.__init__(self)
        self.item2 = textedit2
        self.newpos = self.item2.pos()  # 移動後位置
        print("init newpos", self.newpos)
        self.oldpos = pos  # 原始位置
        print("init oldpos", self.oldpos)

    def undo(self):
        print("oldpos", self.oldpos)
        self.item2.move(self.oldpos)
        print("undo move action")

    def redo(self):
        print("newpos", self.newpos)
        self.item2.move(self.newpos)

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.expanduser = expanduser(":/")
        self.file_load = []
        self.a = 0
        self.step = 0
        self.total = 0  # 上傳的資料夾總共有幾張圖片
        self.now_num = 0  # 目前在第幾張圖片
        self.language = 'zh-TW'
        self.sourcelanguage = 'ja'
        self.lb2 = mylabel(self)
        self.w = self.label_4.width()
        self.h = self.label_4.height()
        self.lb2.setGeometry(QRect(80, 95, 900, 695))
        self.eraserbtn = False
        self.textbtn = False
        self.asd = 0
        self.initWindow()
        self.setMouseTracking(False)
        self.pos_xy = []
        # self.showMaximized()  #開啟是最大化
        # self.setFixedSize(1280,900)  #固定視窗大小

    def initWindow(self):
        self.actionopen.clicked.connect(self.upload_picture)  # 開啟圖檔
        self.actionopen.setShortcut('Ctrl+O')  # 開單張圖片快捷鍵
        self.openfiles.clicked.connect(self.file_dialog)  # 開資料夾
        self.previous_btn.clicked.connect(self.previousPicture)  # 上一張圖片
        self.nextpage_btn.clicked.connect(self.nextPictrue)  # 下一張圖片
        self.pagelist.activated.connect(self.change_combobox)  # combobox顯示張數
        self.erasersize.activated.connect(self.setEraserSize)  # 橡皮擦大小
        self.fontsize.activated.connect(self.setFontSize)  # 文字大小
        self.language2.activated.connect(self.changeLanguage)  # 翻譯選擇
        self.translate.clicked.connect(self.vision_load)  # 翻譯
        self.download_btn.clicked.connect(self.save)  # 下載圖片
        self.actioneraser.clicked.connect(self.eraserOK)  # 橡皮擦
        self.actiontext.clicked.connect(self.textOK)
        self.actionundo.clicked.connect(self.lb2.m_undoaction.trigger)
        self.actionredo.clicked.connect(self.lb2.m_redoaction.trigger)
        self.actionundo.clicked.connect(self.painterundo)
        self.actionredo.clicked.connect(self.painterredo)
        self.actionundo.setShortcut('Ctrl+Z')
        self.actionredo.setShortcut('Ctrl+Y')

    def setEraserSize(self):
        eraserSize = self.erasersize.currentText()
        print(eraserSize)
        self.lb2.getErasersize(eraserSize)

    def setFontSize(self):
        fontSize = self.fontsize.currentText()
        print(fontSize)
        self.lb2.getFontsize(fontSize)

    #清除文字框
    def clear(self):
        print("clear")
        x = 0
        if self.lb2.savetextedit:
            for self.lb2.savetextedit[x] in self.lb2.savetextedit:
                j = self.lb2.savetextedit[x]
                j.deleteLater()
                x = x + 1
            self.lb2.savetextedit.clear()
            self.lb2.undoStack.clear()

    #painter的undo redo
    def painterundo(self):
        if self.eraserbtn == True:
            print("painter undo")
            print("saveimage count",self.lb2.temp_img)
            n = self.lb2.temp_img - 2
            if n > 0:
                img = cv2.imread("./saveload/img{}.PNG".format(n))
                height, width, bytesPerComponent = img.shape
                bytesPerLine = 3 * width
                cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
                self.image = QtGui.QImage(img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
                self.lb2.openimage(self.image)
                self.lb2.temp_img = self.lb2.temp_img - 1
            else:
                self.lb2.openimage(self.QImg)
                self.lb2.temp_img = 1

    def painterredo(self):
        print("painter redo")
        try:
            if self.eraserbtn == True:
                n = self.lb2.temp_img
                img = cv2.imread("./saveload/img{}.PNG".format(n))
                height, width, bytesPerComponent = img.shape
                bytesPerLine = 3 * width
                cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
                self.image = QtGui.QImage(img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
                self.lb2.openimage(self.image)
                self.lb2.temp_img = self.lb2.temp_img + 1
        except Exception as e:
            print(e)

    #視窗關閉事件
    def closeEvent(self, event):
        #清空圖片暫存檔
        try:
            for i in range(1,len(self.lb2.numstack)+1):
                os.remove("./saveload/img{}.PNG".format(i))
        except Exception as e:
            print(e)

    # 上傳單張圖片
    def upload_picture(self):
        self.now_num = 0
        self.file_load = []  # 圖片路徑
        self.file_load, _ = QtWidgets.QFileDialog.getOpenFileNames(self, filter="images(*.jpg OR *.png OR *.pdf) ;; All Files(*.*)")
        print("\npicture : ", self.file_load)

        if self.file_load:  # 判斷是否有選取圖片
            # 為了用橡皮擦功能，所以用另一種方式讀圖片(cv)
            img = cv2.imread(self.file_load[self.now_num])
            height, width, bytesPerComponent = img.shape
            print("img wudth = ",width)
            print("img height = ",height)
            self.picture_width = width
            self.picture_height = height
            self.QImg = QImage(self.file_load[0])

            self.w = self.label_4.width()
            self.h = self.label_4.height()

            self.set_combobox()  # 設定頁數
            self.total = self.calculation_file()
            self.img_num.setText(str(self.now_num + 1) + " / " + str(self.total))  # 顯示圖片張數0/0

            self.lb2.openimage(self.QImg)
            self.clear()

    # 上傳資料夾
    def file_dialog(self):
        self.now_num = 0
        self.file_load = []
        file_path = QtWidgets.QFileDialog.getExistingDirectory(directory=self.expanduser)
        print("\nfile : ", self.file_load)

        if file_path:
            for root, dirs, files in os.walk(file_path):
                for f in files:
                    if (f[-3:] == "jpg" or f[-3:] == "png" or f[-3:] == "pdf" or f[-3:] == "gif" or f[-3:] == "PNG"):
                        data_path = root + "/" + f
                        self.file_load.append(data_path)
                        print("files", self.file_load)

            # 顯示第一張圖片
            img = cv2.imread(self.file_load[0])
            height, width, bytesPerComponent = img.shape
            bytesPerLine = 3 * width
            cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
            self.QImg = QtGui.QImage(img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
            self.w = self.label_4.width()
            self.h = self.label_4.height()
            self.scaredPixmap = self.QImg.scaled(self.w, self.h, aspectRatioMode=Qt.KeepAspectRatio)
            self.label_4.setAlignment(Qt.AlignCenter)  # 圖片置中對齊

            self.set_combobox()
            self.total = self.calculation_file()
            self.img_num.setText(str(self.now_num + 1) + " / " + str(self.total))  # 顯示圖片張數0/0
            self.lb2.openimage(self.QImg)
            self.clear()

    # 設定combobox頁數
    def set_combobox(self):
        self.pagelist.clear()
        combobox = self.calculation_file()
        i = 0
        while combobox > i:
            i = i + 1
            self.pagelist.addItem("Page : %d" % i)

    # 從combobox選顯示的圖片
    def change_combobox(self):
        print(self.pagelist.currentIndex())
        self.now_num = self.pagelist.currentIndex()

        img = cv2.imread(self.file_load[self.now_num])
        height, width, bytesPerComponent = img.shape
        bytesPerLine = 3 * width
        cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
        self.QImg = QtGui.QImage(img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
        self.scaredPixmap = self.QImg.scaled(self.w, self.h, aspectRatioMode=Qt.KeepAspectRatio)
        self.label_4.setAlignment(Qt.AlignCenter)  # 圖片置中對齊
        self.total = self.calculation_file()
        self.img_num.setText(str(self.now_num + 1) + " / " + str(self.total))  # 顯示圖片張數0/0
        self.lb2.openimage(self.QImg)
        self.clear()

    # 計算資料夾有幾張圖片
    def calculation_file(self):
        print("\ncalculation: ", self.file_load)
        file_num = len(self.file_load)
        print("num:", file_num)
        return file_num

    # 下一張圖片
    def nextPictrue(self):
        self.total = self.calculation_file()
        if (self.total - 1 > self.now_num):
            self.now_num = self.now_num + 1
            print("total :", self.total)
            print("now :", self.now_num)
            img = cv2.imread(self.file_load[self.now_num])
            height, width, bytesPerComponent = img.shape
            bytesPerLine = 3 * width
            cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
            self.QImg = QtGui.QImage(img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
            self.scaredPixmap = self.QImg.scaled(self.w, self.h, aspectRatioMode=Qt.KeepAspectRatio)
            self.label_4.setAlignment(Qt.AlignCenter)  # 圖片置中對齊
            self.lb2.openimage(self.QImg)

            self.pagelist.setCurrentIndex(self.now_num)  # combobox數字跟著改
            self.img_num.setText(str(self.now_num + 1) + " / " + str(self.total))  # 顯示圖片張數0/0
            self.clear()
        else:
            self.lb2.openimage(self.QImg)

    # 上一張圖片
    def previousPicture(self):
        self.total = self.calculation_file()
        if (0 < self.now_num):
            self.now_num = self.now_num - 1
            print("total :", self.total)
            print("now :", self.now_num)

            img = cv2.imread(self.file_load[self.now_num])
            height, width, bytesPerComponent = img.shape
            bytesPerLine = 3 * width
            cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
            self.QImg = QtGui.QImage(img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
            self.scaredPixmap = self.QImg.scaled(self.w, self.h, aspectRatioMode=Qt.KeepAspectRatio)
            self.label_4.setAlignment(Qt.AlignCenter)  # 圖片置中對齊
            self.lb2.openimage(self.QImg)
            self.pagelist.setCurrentIndex(self.now_num)  # combobox數字跟著改
            self.img_num.setText(str(self.now_num + 1) + " / " + str(self.total))  # 顯示圖片張數0/0
            self.clear()
        else:
            self.lb2.openimage(self.QImg)

    # 圖片轉換成文字
    def vision_load(self):
        try:
            t = 0
            data = []
            position = []
            text = []
            xy = []
            X_data = []
            Y_data = []
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "Python Vision.json"
            translate_client = translate.Client()  ## 利用vision 進行翻譯
            # Python Vision vision_test
            # 翻譯第0張圖片
            path = self.file_load[self.now_num]
            print("path~~~", path)
            vision_client = vision.ImageAnnotatorClient()

            with io.open(path, 'rb') as image_file:
                content = image_file.read()
                image = types.Image(content=content)
                image_context = vision.types.ImageContext(language_hints=['ja'])
                response = vision_client.text_detection(image=image, image_context=image_context)

            texts = response.full_text_annotation
            print("full text = ", texts.text)
            for page in texts.pages:
                for block in page.blocks:
                    # print("block confidence:{}\n".format(block.confidence))
                    for paragraph in block.paragraphs:
                        # print('Paragraph confidence: {}'.format(paragraph.confidence))
                        for word in paragraph.words:
                            # word_text = ''.join([symbol.text for symbol in word.symbols])
                            # print('Word text: {} (confidence: {})'.format(word_text, word.confidence))
                            for symbol in word.symbols:
                                print(
                                    '\tSymbol: {} (vertices: {})'.format(symbol.text, symbol.bounding_box.vertices))
                                position.append(symbol.bounding_box.vertices)
                                data.append(symbol.text)

            for i in range(0, len(data)):
                print("data", data[i])
                print("position", position[i][-1])
                text.append(data[i])
                xy.append(position[i][-1])
            print("XY = ", xy)  # 拆解locale 變成X Y
            xy_ = "".join(str(i) for i in xy)
            xy_ = xy_.split(":")
            xy_ = "".join(str(i) for i in xy_)
            xy_ = xy_.split(" ")
            xy_ = "".join(str(i) for i in xy_)
            xy_ = xy_.split("\n")
            del xy_[-1]
            print("xy_2 = ", xy_)  # xy交錯著

            for i in xy_:  # 分開X和Y值
                if t == 0:
                    X_data.append(int(i[1::]))
                    t = 1
                else:
                    Y_data.append(int(i[1::]))
                    t = 0

            print("X = ", X_data)
            print("Y = ", Y_data)
            print("data = >", data)
            final_temp_text = self.vision_data_test(data, X_data, Y_data)  # 傳給另外一個def進行後續的排序
            final_text = []
            print("final_temp_text = ", final_temp_text)
            for i in range(0, len(final_temp_text)):
                _text = "".join(str(j) for j in final_temp_text[i])
                final_text.append(_text)
            print("final_text = ", final_text)
            result = translate_client.translate(final_text, target_language=self.language)
            print("result = ", result)
            screen_text = []
            for i in result:
                print(i['input'], "->", i['translatedText'])
                screen_text.append(i['input'] + "\n -> \n" + i['translatedText'] + "\n\n")

            screen_text = "".join(str(i) for i in screen_text)
            self.textArea.setText(screen_text)
        except Exception as e:
            print(e)

    def vision_data_test(self, text, x, y):
        x_data = []  # 暫存
        X_data = []  # 實際存 用來記住不重複的X值
        y_data = []  # 暫存
        Y_data = []  # 實際存 用來記住不重複的Y值
        print("x =", len(x))
        print("y = ", len(y))
        print("text = ", len(text))

        xy_classification = []
        current_text = []
        data = []

        combit = dict(zip(zip(x, y), text))
        data_text = sorted(combit.items(), key=lambda x: x[0], reverse=True)  # 字典X值排序
        print("data_text = ", data_text)

        for i in range(0, len(data_text)):
            data.append(data_text[i][0])

        data_array = np.array(data)

        print("type(data) = ", type(data))
        print("type(data_array) = ", type(data_array))
        print("data = ", data)
        print("data_array = ", data_array)
        print("\ndata_text = ", len(data_text))
        print("data = ", len(data))
        ##尋找K值
        XY_avgs = []
        ks = range(2, 11)

        ##########分群演算法 test ##################
        # try:
        #     only_one_k = False
        #     for k in ks:
        #         kmeans_fit = cluster.KMeans(n_clusters=k).fit(data_array)  # 分群演算法
        #         cluster_labels = kmeans_fit.labels_  # 獲得分權結果
        #         XY_avg = metrics.silhouette_score(data_array, cluster_labels)  # 評估績效數值
        #         XY_avgs.append(XY_avg)  # 存到陣列裡面
        # except:
        #     only_one_k = True
        #     print("just 1")
        ##########分群演算法 test ##################

        ##########分群演算法 DBSCAN ##################
        y_pred = cluster.DBSCAN(eps=38, min_samples=3).fit_predict(data_array)

        print(y_pred)
        K = max(y_pred) + 1
        print("cluster number = ",K)

        if K >= 2:
            only_one_k = False
        else:
            only_one_k = True

        # plt.scatter(data_array[:, 0], data_array[:, 1], c=y_pred)
        # plt.show()
        ##########分群演算法 DBSCAN ##################

        # 作圖並印出 k = 2 到 10 的績效
        #        plt.bar(ks, XY_avgs)
        #        plt.show()
        #        print(XY_avgs)
        if (not only_one_k):
            # K = XY_avgs.index(max(XY_avgs)) + 2
            # print("K = ", K)
            # km = cluster.KMeans(n_clusters=K)
            # y_pred = km.fit_predict(data_array)
            # print("y = ", y_pred)
            # print("y = ", len(y_pred))

            print("data_text = ", len(data_text))
            K = K - 1
            while (K >= 0):
                for i in range(0, len(y_pred)):
                    if (K == y_pred[i]):
                        print("K =", K)
                        print("data_array[i] = ", data_text[i])
                        xy_classification.append(data_text[i])
                K -= 1
                current_text.append(copy.deepcopy(xy_classification))
                xy_classification.clear()
        else:
            current_text = data_text

               # plt.figure()
        #        plt.xlabel('x')
        #        plt.ylabel('y')
        #        plt.scatter(data_array[:, 0], data_array[:, 1], c=y_pred) #C是第三維度 已顏色做維度
        #        plt.show()
        for i in current_text:
            print("current_text = ", i)

        for i in range(0, len(current_text)):
            print("current_text len = ", len(current_text[i]))


        ######### 去除離群值 2~3倍標準差##########
        x = []
        cluster_x_data = []
        cluster_x_mean = []
        cluster_x_std = []
        outliners = []
        outliners_text = []
        for i in range(0, len(current_text)):  # 把X值抓出來
            if (only_one_k):
                x.append(current_text[i][0][0])
            else:
                for j in range(0, len(current_text[i])):
                    x.append(current_text[i][j][0][0])
            cluster_x_data.append(copy.deepcopy(x))
            x.clear()

        print("cluster_x_data = ", cluster_x_data)

        if (only_one_k):  # 先取得標準差 及 平均值
            cluster_x_mean.append(np.mean(cluster_x_data))
            cluster_x_std.append(np.std(cluster_x_data))
            positive_mean_2std = cluster_x_mean[0] + 3 * cluster_x_std[0]
            negative_mean_2std = cluster_x_mean[0] - 3 * cluster_x_std[0]
            print("positive_mean_2std = ", positive_mean_2std)
            print("negative_mean_2std = ", negative_mean_2std)
        else:
            for i in range(0, len(cluster_x_data)):
                o_mean = np.mean(cluster_x_data[i])
                o_std = np.std(cluster_x_data[i])
                print("o_mean", o_mean)
                print("o_std", o_std)
                cluster_x_mean.append(o_mean)
                cluster_x_std.append(o_std)
        print("cluster_x_mean = ", cluster_x_mean)
        print("cluster_x_std = ", cluster_x_std)

        print("current_text = ", current_text)
        for i in range(0, len(current_text)):  # 去除離群值
            if (only_one_k):
                if (negative_mean_2std <= current_text[i][0][0] <= positive_mean_2std):
                    outliners_text.append(current_text[i])
            else:
                positive_mean_2std = cluster_x_mean[i] + 3 * cluster_x_std[i]
                negative_mean_2std = cluster_x_mean[i] - 3 * cluster_x_std[i]
                print("positive_mean_2std = ", positive_mean_2std)
                print("negative_mean_2std = ", negative_mean_2std)
                for j in range(0, len(current_text[i])):
                    if (negative_mean_2std <= current_text[i][j][0][0] <= positive_mean_2std):
                        outliners.append(current_text[i][j])
                outliners_text.append(copy.deepcopy(outliners))
                outliners.clear()

        print("current_text = ", current_text)
        print("outliners_text = ", outliners_text)
        ######### 去除離群值 ##########

        minus_x = []  # 暫存
        Minus_x = []  # 實際存 用來記住每個分群的X相差值
        minus_avgs_x = []  # 存X差平均值
        minus_y = []  # 暫存
        Minus_y = []  # 實際存 用來記住每個分群的y相差值
        minus_avgs_y = []  # 存y差平均值
        mean_x = []
        mean_y = []
        std_x = []
        std_y = []
        ######### 計算陣列xy的差異值、平均值、標準差 ##########
        for i in range(0, len(outliners_text)):  # 去除重複的X值
            if (only_one_k):
                if not outliners_text[i][0][0] in x_data:
                    x_data.append(outliners_text[i][0][0])

                if not outliners_text[i][0][1] in y_data:
                    y_data.append(outliners_text[i][0][1])
                X_data = x_data
                Y_data = y_data
            else:
                for j in range(0, len(outliners_text[i])):
                    print("i", outliners_text[i][j][0][0])
                    if not outliners_text[i][j][0][0] in x_data:
                        x_data.append(outliners_text[i][j][0][0])

                    if not outliners_text[i][j][0][1] in y_data:
                        y_data.append(outliners_text[i][j][0][1])

                X_data.append(copy.deepcopy(x_data))
                x_data.clear()

                y_data = sorted(y_data, reverse=True)  # Y值排序由大到小
                Y_data.append(copy.deepcopy(y_data))
                y_data.clear()

        print("X_data===", X_data)
        print("Y_data===", Y_data)

        if (only_one_k):  # 把取得的值相減
            Y_data = sorted(Y_data, reverse=True)
            print("Y_data===", Y_data)
            for i in range(1, len(X_data)):
                m = int(X_data[i - 1] - X_data[i])
                Minus_x.append(m)

            for i in range(1, len(Y_data)):
                m = int(Y_data[i - 1] - Y_data[i])
                Minus_y.append(m)

            std_x = np.std(Minus_x)
            std_y = np.std(Minus_y)

            minus_avgs_x = np.mean(Minus_x)
            minus_avgs_y = np.mean(Minus_y)
        else:
            for i in range(0, len(X_data)):  # 把取得的值相減
                while (len(X_data[i]) != 1):  # 把X值相減
                    m = int(X_data[i][0]) - int(X_data[i][1])
                    minus_x.append(m)
                    del X_data[i][0]
                if (minus_x != []):
                    Minus_x.append(copy.deepcopy(minus_x))
                    minus_x.clear()
                else:
                    Minus_x.append([0])
                    minus_x.clear()

                while (len(Y_data[i]) != 1):  # 把Y值相減
                    m = int(Y_data[i][0]) - int(Y_data[i][1])
                    minus_y.append(m)
                    del Y_data[i][0]
                if (minus_y != []):
                    Minus_y.append(copy.deepcopy(minus_y))
                    minus_y.clear()
                else:
                    Minus_y.append([0])
                    minus_y.clear()

            for i in range(0, len(Minus_x)):
                ## 因為mean 不能為0
                sum_x = 0
                sum_y = 0
                print("np.mean(Minus_x[i]) = ", np.mean(Minus_x[i]))
                print("np.mean(Minus_y[i]) = ", np.mean(Minus_y[i]))
                for j in range(0, len(Minus_x[i])):
                    sum_x += (Minus_x[i][j] - np.mean(Minus_x[i])) ** 2

                for j in range(0, len(Minus_y[i])):
                    sum_y += (Minus_y[i][j] - np.mean(Minus_y[i])) ** 2

                mean_x.append(sum_x)
                mean_y.append(sum_y)

            for i in range(0, len(mean_x)):
                x = int(round(np.sqrt(mean_x[i] / len(Minus_x[i])), 0))
                y = int(round(np.sqrt(mean_y[i] / len(Minus_y[i])), 0))
                std_x.append(x)
                std_y.append(y)

            for i in range(0, len(Minus_x)):  # 取X相差的平均值 當作一個依據
                minus_x = int(round(np.mean(Minus_x[i]), 0))
                minus_avgs_x.append(minus_x)

                minus_y = int(round(np.mean(Minus_y[i]), 0))
                minus_avgs_y.append(minus_y)

        print("minus=x===", Minus_x)
        print("minus=y===", Minus_y)
        print("mean_x===", mean_x)
        print("mean_y===", mean_y)
        print("std_x===", std_x)
        print("std_y===", std_y)
        print("minus=x===", minus_avgs_x)
        print("minus=y===", minus_avgs_y)
        ######### 計算陣列xy的差異值、平均值、標準差 ##########

        temp_text = []  # 暫存文字
        final = []  # 最後文字
        final_loop = []

        ######### 根據算出來的平均值、標準差當作一個依據 進行排列 ##########
        print("current_text = ", current_text)
        print("current len = ", len(current_text))
        if (only_one_k):
            l = 2
            print("len = ", len(current_text))
            for i in range(1, len(current_text)):
                temp = current_text[i]
                k = i - 1
                if (l == len(current_text)):
                    print("<avg + std len - 1= ", current_text[k])
                    print("<avg + std len_max= ", temp)
                    temp_text.append(current_text[k])
                    _final = sorted(temp_text, key=lambda x: x[0][1])
                    final.append(copy.deepcopy(_final))
                    temp_text.clear()
                    print("final = ", final)
                else:
                    if (current_text[k][0][0] - temp[0][0]) <= minus_avgs_x:
                        print("<avg + std = ", current_text[k])
                        temp_text.append(current_text[k])
                    else:
                        temp_text.append(current_text[k])
                        print(">avg + std = ", current_text[k])
                        _final = sorted(temp_text, key=lambda x: x[0][1])
                        final.append(copy.deepcopy(_final))
                        temp_text.clear()
                        print("final = ", final)
                l += 1
                print("l = ", l)
        else:
            for i in range(0, len(current_text)):  # 根據minus 的平均值來重新排列
                l = 1  # 判斷是否是最後一行
                for j in range(1, len(current_text[i])):
                    temp = current_text[i][j]
                    k = j - 1
                    l += 1
                    if (l == len(current_text[i])):
                        print("<avg + std len - 1= ", current_text[i][k])
                        print("<avg + std len_max= ", temp)
                        temp_text.append(current_text[i][k])
                        temp_text.append(temp)
                        _final = sorted(temp_text, key=lambda x: x[0][1])
                        final.append(copy.deepcopy(_final))
                        temp_text.clear()
                    else:
                        if (current_text[i][k][0][0] - temp[0][0]) <= minus_avgs_x[i]:
                            temp_text.append(current_text[i][k])
                            print("<avg + std = ", current_text[i][k])
                        else:
                            temp_text.append(current_text[i][k])
                            _final = sorted(temp_text, key=lambda x: x[0][1])
                            final.append(copy.deepcopy(_final))
                            temp_text.clear()
                            print(">avg + std = ", current_text[i][k])
                final_loop.append(copy.deepcopy(final))
                final.clear()

        print("final_loop = ", final_loop)
        ######### 根據算出來的平均值、標準差當作一個依據 進行排列 ##########

        final_text = []
        ######### 解析排列 -> 抓出文字 ##########
        if (only_one_k):
            for i in range(0, len(final)):
                for j in range(0, len(final[i])):
                    final_text.append(final[i][j][1])
        else:
            for i in range(0, len(final_loop)):
                for j in range(0, len(final_loop[i])):
                    for k in range(0, len(final_loop[i][j])):
                        temp_text.append(final_loop[i][j][k][1])
                final_text.append(copy.deepcopy(temp_text))
                temp_text.clear()

        print("final_text = ", final_text)
        return final_text
        ######### 解析排列 -> 抓出文字 ##########


##下載圖片(文字)
    def vision_download(self):
        print("vision_download:", self.vision_data[0])
        self.fileName, _ = QtWidgets.QFileDialog.getSaveFileName(filter="Text Files(*.txt) ;; All Files(*.*)")
        if self.fileName:
            print(self.fileName)

    # 最終的橡皮擦
    def eraserOK(self):
        if self.eraserbtn == False:
            self.eraserbtn = True
            # self.actioneraser.setDown(True)  #按鈕下壓的感覺
            self.textbtn = False
            self.lb2.textClicked = False
            self.lb2.setGeometry(QRect(80, 95, 900, 695))
            self.lb2.setEnabled(True)
            self.lb2.eraserClicked = True
            print("eraserbtnClicked", self.eraserbtn)
        else:
            self.eraserbtn = False
            self.lb2.eraserClicked = False
            self.lb2.setEnabled(False)
            print("eraserbtnClicked", self.eraserbtn)

    def textOK(self):
        if self.textbtn == False:
            self.textbtn = True
            self.eraserbtn = False
            self.lb2.eraserClicked = False
            self.lb2.setGeometry(QRect(80, 95, 900, 695))
            self.lb2.setEnabled(True)
            self.lb2.textClicked = True
            print("textbtnClicked", self.textbtn)
        else:
            self.textbtn = False
            self.lb2.textClicked = False
            self.lb2.setEnabled(False)
            print("textbtnClicked", self.textbtn)

    def save(self):
        print("save")
        self.lb2.textClicked = False
        self.fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            filter="Text Files(*.jpg OR *.png OR *.pdf) ;; All Files(*.*)")
        print(self.fileName)
        if self.fileName:
            pqscreen = QtGui.QGuiApplication.primaryScreen()
            self.px = self.lb2.pos()
            x = self.lb2.width() - self.lb2.image.width()
            y = self.lb2.height() - self.lb2.image.height()
            self.lbposx = self.px.x() + x/2
            self.lbposy = self.px.y() + y/2
            pixmap = pqscreen.grabWindow(self.winId(),self.lbposx,self.lbposy,self.lb2.image.width(),self.lb2.image.height())
            pixmap.save(self.fileName)

    def changeLanguage(self):
        print("change")
        if self.language2.currentIndex() == 0:
            self.language = 'zh-TW'
        elif self.language2.currentIndex() == 1:
            self.language = 'ja'
        else:
            self.language = 'en'

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())