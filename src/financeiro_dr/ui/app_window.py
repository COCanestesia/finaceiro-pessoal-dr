from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame,QHBoxLayout,QLabel,QMainWindow,QPushButton,QScrollArea,QStackedWidget,QVBoxLayout,QWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('Financeiro Pessoal do Dr.');self.resize(1440,900);self._page_indexes={};self._buttons={}
        root=QWidget();root_layout=QHBoxLayout(root);root_layout.setContentsMargins(0,0,0,0);root_layout.setSpacing(0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(245);self.sidebar_layout=QVBoxLayout(sidebar);self.sidebar_layout.setContentsMargins(14,18,14,18)
        brand=QLabel('Financeiro\nPessoal do Dr.');brand.setObjectName('brand');brand.setAlignment(Qt.AlignLeft|Qt.AlignVCenter);self.sidebar_layout.addWidget(brand);self.sidebar_layout.addSpacing(12)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setStyleSheet('background: transparent;');menu=QWidget();menu.setStyleSheet('background: transparent;');self.menu_layout=QVBoxLayout(menu);self.menu_layout.setContentsMargins(0,0,0,0);self.menu_layout.setSpacing(3);self.menu_layout.addStretch(1);scroll.setWidget(menu);self.sidebar_layout.addWidget(scroll,1)
        self.stack=QStackedWidget();root_layout.addWidget(sidebar);root_layout.addWidget(self.stack,1);self.setCentralWidget(root)
        self.setStyleSheet("QFrame#sidebar{background:#18202a;} QLabel#brand{color:white;font-size:20px;font-weight:700;} QFrame#sidebar QPushButton{min-height:30px;text-align:left;padding:8px 10px;color:#eef2f6;border:0;border-radius:6px;} QFrame#sidebar QPushButton:hover{background:#2b3948;} QFrame#sidebar QPushButton:checked{background:#35475a;font-weight:600;} QStackedWidget{background:#f6f7f9;}")
    def add_page(self,key:str,title:str,widget:QWidget)->None:
        if key in self._page_indexes:raise ValueError(f'Página já cadastrada: {key}')
        index=self.stack.addWidget(widget);self._page_indexes[key]=index;button=QPushButton(title);button.setCheckable(True);button.clicked.connect(lambda checked=False,page_key=key:self.show_page(page_key));self.menu_layout.insertWidget(self.menu_layout.count()-1,button);self._buttons[key]=button
        if len(self._page_indexes)==1:self.show_page(key)
    def show_page(self,key:str)->None:
        self.stack.setCurrentIndex(self._page_indexes[key])
        for name,button in self._buttons.items():button.setChecked(name==key)
        widget=self.stack.currentWidget()
        if hasattr(widget,'refresh'):
            try:widget.refresh()
            except Exception:pass
