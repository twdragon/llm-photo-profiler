#!/usr/bin/env python3

# Import sections
import sys
from pathlib import Path
import re
import base64
from copy import deepcopy
import pyexiv2
# import requests
from PyQt6.QtCore import (
    Qt, 
    QSettings,
    QSize,
    QAbstractTableModel,
    QVariant,
    QByteArray,
    QBuffer,
    QIODevice,
    QRegularExpression,
    QCoreApplication,
    QProcess,
    QJsonDocument,
    QUrl,
    QItemSelectionModel,
    QEventLoop
)
from PyQt6.QtGui import (
    QAction,
    QIcon,
    QPixmap,
    QFont,
    QImage,
    QRegularExpressionValidator,
    QIntValidator,
    QFontMetrics,
    QKeySequence
)
from PyQt6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QWidget, 
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QListWidget, 
    QTabWidget, 
    QToolBar, 
    QStatusBar, 
    QMenuBar,
    QListWidgetItem,
    QStyle,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QGroupBox,
    QTableView,
    QHeaderView,
    QLineEdit,
    QLabel,
    QPushButton,
    QCheckBox,
    QPlainTextEdit,
    QSlider,
    QLabel
)
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkRequest,
    QNetworkReply
)

# Default prompts
short_default_prompt = '''Please generate a JSON object containing the following metadata for the image I uploaded with this message. Return only the JSON and nothing more. Do not use Markdown. Never use long dashes. Here is the field set of the JSON you should generate:

- `title`: A comprehensive, precise, concise title describing the principal depicted object, visually relevant setting and photographic style, not more than 12 words. Do not use subjective claims such as “beautiful,” “amazing,” or “stunning” unless the visual style clearly requires them.
- `keywords`: a JSON array of 20-50 keywords precisely describing the image to make it findable and recognisable in the photolicensing database. Every keyword must be exactly one word, lowercase, with no use spaces, hyphens, underscores, slashes, punctuation, or concatenated words inside a keyword.
- `description`: a concise paragraph of text (no more than 100 words) precisely describing the image, its style, mood and atmosphere. Limit strictly the usage of subjective claims such as “beautiful,” “amazing,” or “stunning” unless the visual style clearly requires them.
'''

# Internal API
class Profiler:
    def __init__(self):
        self.current_directory = Path(__file__).resolve().parent
        self.photographs_list = list()
        self.supported_files_regex = re.compile(r'(^.*)\.(jpg|jpeg|tif|tiff|png|ping)$', re.IGNORECASE)
        self.metadata = dict()
        self.index = -1

    def probe_directory(self, directory: Path):
        probe_list = list()
        if directory != self.current_directory:
            for f in directory.iterdir():
                if self.supported_files_regex.fullmatch(str(f.name)) is not None:
                    probe_list.append(f)
            if probe_list:
                self.photographs_list.clear()
                self.photographs_list = deepcopy(probe_list)
                return True
            return False
        else:
            return False

    def load_metadata(self, index: int):
        temp_image_handler = self.photographs_list[index].open('rb')
        temp_image = pyexiv2.ImageData(temp_image_handler.read())
        temp_image_handler.close()
        result = dict()
        exif_metadata = temp_image.read_exif()
        if exif_metadata:
            result['EXIF'] = exif_metadata
        iptc_metadata = temp_image.read_iptc()
        if iptc_metadata:
            result['IPTC'] = iptc_metadata
        xmp_metadata = temp_image.read_xmp()
        if xmp_metadata:
            result['XMP'] = xmp_metadata
        temp_image.close()
        self.metadata.clear()
        self.metadata = deepcopy(result)
        self.index = index
        return result

    def clear_metadata(self):
        if self.index != -1:
            temp_image_handler = self.photographs_list[self.index].open('rb')
            temp_image = pyexiv2.ImageData(temp_image_handler.read())
            temp_image_handler.close()
            temp_image.clear_exif()
            temp_image.clear_iptc()
            temp_image.clear_xmp()
            temp_image.clear_comment()
            temp_image.clear_icc()
            temp_image.clear_thumbnail()
            temp_image_handler = self.photographs_list[self.index].open('wb')
            temp_image_handler.write(temp_image.get_bytes())
            temp_image_handler.close()
            temp_image.close()
            
    def truncate_metadata(self):
        if self.index != -1:
            self.remove_descriptive_metadata()
            temp_image_handler = self.photographs_list[self.index].open('rb')
            temp_image = pyexiv2.ImageData(temp_image_handler.read())
            temp_image_handler.close()
            temp_image.clear_xmp()
            temp_image.clear_comment()
            temp_image.clear_thumbnail()
            exif_metadata = temp_image.read_exif()
            if exif_metadata:
                if 'Exif.Image.Software' in exif_metadata.keys():
                    del exif_metadata['Exif.Image.Software']
            temp_image.clear_exif()
            temp_image.modify_exif(exif_metadata)
            temp_image_handler = self.photographs_list[self.index].open('wb')
            temp_image_handler.write(temp_image.get_bytes())
            temp_image_handler.close()
            temp_image.close()

    def update_metadata(self, metadata: dict):
        if self.index != -1 and any(metadata.values()):
            temp_image_handler = self.photographs_list[self.index].open('rb')
            temp_image = pyexiv2.ImageData(temp_image_handler.read())
            temp_image_handler.close()
            temp_image.modify_iptc(metadata)
            temp_image_handler = self.photographs_list[self.index].open('wb')
            temp_image_handler.write(temp_image.get_bytes())
            temp_image_handler.close()
            temp_image.close()

    def remove_descriptive_metadata(self):
        if self.index != -1:
            temp_image_handler = self.photographs_list[self.index].open('rb')
            temp_image = pyexiv2.ImageData(temp_image_handler.read())
            temp_image_handler.close()
            iptc_metadata = temp_image.read_iptc()
            if iptc_metadata:
                if 'Iptc.Application2.ObjectName' in iptc_metadata.keys():
                    del iptc_metadata['Iptc.Application2.ObjectName']
                if 'Iptc.Application2.Keywords' in iptc_metadata.keys():
                    del iptc_metadata['Iptc.Application2.Keywords']
                if 'Iptc.Application2.Caption' in iptc_metadata.keys():
                    del iptc_metadata['Iptc.Application2.Caption']
                temp_image.clear_iptc()
                temp_image.modify_iptc(iptc_metadata)
                temp_image_handler = self.photographs_list[self.index].open('wb')
                temp_image_handler.write(temp_image.get_bytes())
                temp_image_handler.close()
                temp_image.close()


    def base64_llm_data(self) -> str:
        if self.index != -1:
            source_image = QImage(str(self.photographs_list[self.index]))
            scaled_image = source_image.scaled(QSize(800, 800), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            encoded_bytes = QByteArray()
            buffer = QBuffer(encoded_bytes)
            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
            scaled_image.save(buffer, 'jpg', 90)
            encoded = base64.b64encode(encoded_bytes.data()).decode('utf-8')
            return 'data:{};base64,{}'.format('image/jpeg', encoded)

# GUI
class FullMetadataViewModel(QAbstractTableModel):
    def __init__(self, data: list[tuple]):
        super().__init__()
        self.data = data
    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            row, col = index.row(), index.column()
            return str(self.data[row][col])
    def rowCount(self, index): 
        return len(self.data)
    def columnCount(self, index): 
        return 2
    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return 'Parameter'
            elif section == 1:
                return 'Value'
        return QVariant()

class ProfilerWindow(QMainWindow):
    def __init__(self, profiler_api):
        super().__init__()
        QCoreApplication.setOrganizationName('twdragon')
        QCoreApplication.setOrganizationDomain('gallery.twdragon.net')
        QCoreApplication.setApplicationName('LLM Photo Profiler')
        self.settings = QSettings()
        self.profiler = profiler_api
        self.filename_map = dict()
        self.last_directory = Path(__file__).resolve().parent
        mono_font = QFont("Monospace")
        mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.llm_server_process = None
        self.have_server = False
        self.have_model = False
        self.have_mmproj = False
        self.have_mtp = False
        self.icon_size = 100
        self.app_timeout = 3000
        self.netproc = QNetworkAccessManager(self)
        self.llm_response = str()
# Creating action callbacks
        # Load & Enumerate
        actionLoadImages = QAction('Load &Directory', self)
        actionLoadImages.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart))
        actionLoadImages.triggered.connect(self.enumerate_directory)
        actionLoadImages.setShortcut(QKeySequence('Ctrl+o'))
        # Save current edits
        actionSaveEdits = QAction('&Save Edits', self)
        actionSaveEdits.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        actionSaveEdits.triggered.connect(self.save_edited)
        actionSaveEdits.setShortcut(QKeySequence('Ctrl+s'))
        # Check connection
        actionCheckServer = QAction('Connect to LLM Server', self)
        actionCheckServer.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_CommandLink))
        actionCheckServer.triggered.connect(self.test_llm_server_connect)
        actionCheckServer.setShortcut(QKeySequence('F5'))
        # Run server
        actionRunServer = QAction('Run local &LLM Server', self)
        actionRunServer.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        actionRunServer.triggered.connect(self.llm_server_run)
        actionRunServer.setShortcut(QKeySequence('Ctrl+r'))
        # Stop server
        actionStopServer = QAction('Stop local LLM Server', self)
        actionStopServer.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        actionStopServer.triggered.connect(self.llm_server_stop)
        actionStopServer.setShortcut(QKeySequence('Ctrl+Shift+r'))
        # Quit system
        actionQuit = QAction('&Quit', self)
        actionQuit.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        actionQuit.triggered.connect(self.close)
        actionQuit.setShortcut(QKeySequence('Ctrl+w'))
        # Process Current
        actionProcessImage = QAction('&Process Selected Image', self)
        actionProcessImage.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        actionProcessImage.setShortcut(QKeySequence('F9'))
        actionProcessImage.triggered.connect(self.process_image)
        # Process all
        actionProcessAll = QAction('Process &All Images', self)
        actionProcessAll.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        actionProcessAll.setShortcut(QKeySequence('Shift+Ctrl+F9'))
        actionProcessAll.triggered.connect(self.process_all)
        # Clear metadata
        actionClearMetadata = QAction('&Clear Metadata', self)
        actionClearMetadata.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton))
        actionClearMetadata.triggered.connect(self.clear_metadata)
        # Truncate metadata
        actionTruncateMetadata = QAction('&Truncate Metadata to Minimal IPTC', self)
        actionTruncateMetadata.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        actionTruncateMetadata.triggered.connect(self.truncate_metadata)
        # Purge descriptive
        actionPurgeDescription = QAction('Purge &descriptive metadata (Title, Keywords, Description)', self)
        actionPurgeDescription.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        actionPurgeDescription.triggered.connect(self.purge_descriptive)
# Creating global GUI objects
        self.setWindowTitle('LLM Photo Profiler')
        menu = self.menuBar()
        main_container = QWidget(self)
        main_layout = QHBoxLayout(main_container)
        toolbar = QToolBar('Profiler', self)
        toolbar.setMovable(False)
        toolbar.setObjectName('MainToolbar')
        self.addToolBar(toolbar)
        status = QStatusBar(self)
        self.setStatusBar(status)
        self.setCentralWidget(main_container)
        self.main_progress = QProgressBar()
        self.main_progress.setMaximumHeight(16) 
        status.addPermanentWidget(self.main_progress)
        status.showMessage('GUI loaded')
        self.error_message_dialog = QMessageBox(self)
        self.error_message_dialog.setWindowTitle('Error')
        self.question_dialog = QMessageBox(self)
        self.question_dialog.setWindowTitle('Are you sure?')
# Creating GUI user controllers
        # Menu bar: File
        file_menu = menu.addMenu('&File')
        file_menu.addAction(actionLoadImages)
        file_menu.addSeparator()
        file_menu.addAction(actionProcessImage)
        file_menu.addAction(actionProcessAll)
        file_menu.addSeparator()
        file_menu.addAction(actionQuit)
        # Menu bar: Metadata
        metadata_menu = menu.addMenu('&Metadata')
        metadata_menu.addAction(actionSaveEdits)
        metadata_menu.addSeparator()
        metadata_menu.addAction(actionPurgeDescription)
        metadata_menu.addAction(actionTruncateMetadata)
        metadata_menu.addSeparator()
        metadata_menu.addAction(actionClearMetadata)
        # Menu bar: LLM
        llm_menu = menu.addMenu('&LLM / Server')
        llm_menu.addAction(actionCheckServer)
        llm_menu.addAction(actionRunServer)
        llm_menu.addSeparator()
        llm_menu.addAction(actionStopServer)
        # Menu bar: About
        help_menu = menu.addMenu('&Help')
        help_menu.addAction(QAction('&About', self))
        # Toolbar: Main
        toolbar.addAction(actionLoadImages)
        toolbar.addAction(actionSaveEdits)
        toolbar.addAction(actionProcessImage)
        toolbar.insertSeparator(actionProcessImage)
        toolbar.addAction(actionProcessAll)
        toolbar.addAction(actionPurgeDescription)
        toolbar.insertSeparator(actionPurgeDescription)
        toolbar.addAction(actionTruncateMetadata)
        toolbar.addAction(actionClearMetadata)
        toolbar.addAction(actionCheckServer)
        toolbar.insertSeparator(actionCheckServer)
        toolbar.addAction(actionRunServer)
        toolbar.addAction(actionStopServer)
        # Image list
        self.images_list = QListWidget(self)
        self.images_list.setIconSize(QSize(100,100))
        self.images_list.currentItemChanged.connect(self.select_photograph)
        # Tabbed Panels
        self.tabs = QTabWidget(self)
        self.current_image_tab = QWidget(self)
        self.settings_tab = QWidget(self)
        self.log_tab = QWidget(self)
        self.tabs.addTab(self.current_image_tab, 'Image')
        self.tabs.addTab(self.settings_tab, 'Settings')
        self.tabs.addTab(self.log_tab, 'Log')
        # Split layout
        self.main_splitter = QSplitter(self)
        self.main_splitter.addWidget(self.images_list)
        self.main_splitter.addWidget(self.tabs)
        main_layout.addWidget(self.main_splitter)
# Image metadata panel
        image_metadata_layout = QVBoxLayout(self.current_image_tab)
        self.metadata_group_box = QGroupBox('Full Metadata', self.current_image_tab)
        image_metadata_layout.addWidget(self.metadata_group_box)
        self.metadata_table = QTableView(self.metadata_group_box)
        self.metadata_table_horizontal_header = self.metadata_table.horizontalHeader()
        self.metadata_table_horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.metadata_table_horizontal_header.setStretchLastSection(True)
        self.metadata_table.verticalHeader().hide()
        self.metadata_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.metadata_table_model = FullMetadataViewModel(list())
        self.metadata_table.setModel(self.metadata_table_model)
        metadata_group_box_layout = QVBoxLayout(self.metadata_group_box)
        metadata_group_box_layout.addWidget(self.metadata_table)
        self.metadata_table.setFont(mono_font)
        self.metadata_table.horizontalHeader().setFont(QFont())
        # Selected metadata: title
        self.title_group_box = QGroupBox('Title', self.current_image_tab)
        image_metadata_layout.addWidget(self.title_group_box)
        self.title_field = QLineEdit(self.title_group_box)
        self.title_field.setFont(mono_font)
        title_group_box_layout = QVBoxLayout(self.title_group_box)
        title_group_box_layout.addWidget(self.title_field)
        # Keywords
        self.keyword_group_box = QGroupBox('Keywords', self.current_image_tab)
        image_metadata_layout.addWidget(self.keyword_group_box)
        self.keyword_field = QLineEdit(self.keyword_group_box)
        self.keyword_field.setFont(mono_font)
        keyword_group_box_layout = QVBoxLayout(self.keyword_group_box)
        keyword_group_box_layout.addWidget(self.keyword_field)
        keyword_validator = QRegularExpressionValidator(QRegularExpression('(([[:alnum:]]+)(,|;|:)([[:space:]])?)+([[:alnum:]]+)$'), self.keyword_field)
        self.keyword_field.setValidator(keyword_validator)
        # Description
        self.description_group_box = QGroupBox('Description', self.current_image_tab)
        image_metadata_layout.addWidget(self.description_group_box)
        self.description_field = QPlainTextEdit(self.description_group_box)
        self.description_field.setFont(mono_font)
        description_group_box_layout = QVBoxLayout(self.description_group_box)
        description_group_box_layout.addWidget(self.description_field)
        self.purge_descriptive_btn = QPushButton('Purge descriptive metadata', self.current_image_tab)
        self.purge_descriptive_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        image_metadata_layout.addWidget(self.purge_descriptive_btn)
        self.purge_descriptive_btn.clicked.connect(self.purge_descriptive)
        image_metadata_layout.setStretch(0, 100)
        image_metadata_layout.setStretch(1, 1)
        image_metadata_layout.setStretch(2, 1)
        image_metadata_layout.setStretch(3, 1)
# Settings panel
        settings_layout = QVBoxLayout(self.settings_tab)
        # LLM server group
        self.llm_settings_group_box = QGroupBox('LLM server', self.settings_tab)
        settings_layout.addWidget(self.llm_settings_group_box)
        llm_settings_group_box_layout = QGridLayout(self.llm_settings_group_box)
        # LLM server executable
        llm_server_executable_label = QLabel('Server executable:', self.llm_settings_group_box)
        self.llm_server_executable = QLineEdit(self.settings.value('llm/server/executable') if self.settings.contains('llm/server/executable') else 'llama-server', self.llm_settings_group_box)
        self.llm_server_executable_btn = QPushButton('Select', self.llm_settings_group_box)
        self.llm_server_executable_btn.clicked.connect(self.select_llm_server_executable)
        # LLM server URI
        llm_server_uri_label = QLabel('Server hostname / port:', self.llm_settings_group_box)
        self.llm_server_uri = QLineEdit(self.settings.value('llm/server/uri') if self.settings.contains('llm/server/uri') else '127.0.0.1', self.llm_settings_group_box)
        self.llm_server_port = QLineEdit(self.settings.value('llm/server/port') if self.settings.contains('llm/server/port') else '8080', self.llm_settings_group_box)
        self.llm_server_port.setValidator(QIntValidator())
        font_meter = QFontMetrics(self.llm_server_port.font())
        port_num_size = font_meter.size(0, 'NNNNN').width()
        self.llm_server_port.setFixedWidth(port_num_size)
        llm_server_api_key_label = QLabel('Server API key:', self.llm_settings_group_box)
        self.llm_server_api_key = QLineEdit(self.settings.value('llm/server/key') if self.settings.contains('llm/server/key') else str(), self.llm_settings_group_box)
        self.llm_server_auth = QCheckBox('Authentication', self.llm_settings_group_box)
        if self.settings.contains('llm/server/auth'):
            self.llm_server_auth.setCheckState(Qt.CheckState.Checked if self.settings.value('llm/server/auth') == 'CheckState.Checked' else Qt.CheckState.Unchecked)
        # LLM model file
        llm_server_model_label = QLabel('Local LLM model file:', self.llm_settings_group_box)
        self.llm_server_model = QLineEdit(self.settings.value('llm/server/model') if self.settings.contains('llm/server/model') else str(), self.llm_settings_group_box)
        self.llm_server_model_btn = QPushButton('Select', self.llm_settings_group_box)
        self.llm_server_model_btn.clicked.connect(self.select_llm_server_model)
        # LLM multimodal projector file
        llm_server_mmproj_label = QLabel('Multimodal projector file:', self.llm_settings_group_box)
        self.llm_server_mmproj = QLineEdit(self.settings.value('llm/server/mmproj') if self.settings.contains('llm/server/mmproj') else str(), self.llm_settings_group_box)
        self.llm_server_mmproj_btn = QPushButton('Select', self.llm_settings_group_box)
        self.llm_server_mmproj_btn.clicked.connect(self.select_llm_server_mmproj)
        # LLM MTP draft adaptor file
        llm_server_mtp_label = QLabel('MTP draft model file:', self.llm_settings_group_box)
        self.llm_server_mtp = QLineEdit(self.settings.value('llm/server/mtp') if self.settings.contains('llm/server/mtp') else '', self.llm_settings_group_box)
        self.llm_server_mtp_btn = QPushButton('Select', self.llm_settings_group_box)
        self.llm_server_mtp_btn.clicked.connect(self.select_llm_server_mtp)
        # LLM server flags
        self.llm_server_use_mmap = QCheckBox('Memory mapping', self.llm_settings_group_box)
        if self.settings.contains('llm/server/mmap'):
            self.llm_server_use_mmap.setCheckState(Qt.CheckState.Checked if self.settings.value('llm/server/mmap') == 'CheckState.Checked' else Qt.CheckState.Unchecked)
        else:
            self.llm_server_use_mmap.setCheckState(Qt.CheckState.Checked)
        self.llm_server_unlimited_context = QCheckBox('Context window (set the flag for unlimited)', self.llm_settings_group_box)
        self.llm_server_unlimited_context.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        if self.settings.contains('llm/server/unlimited_context'):
            self.llm_server_unlimited_context.setCheckState(Qt.CheckState.Checked if self.settings.value('llm/server/unlimited_context') == 'CheckState.Checked' else Qt.CheckState.Unchecked)
        else:
            self.llm_server_unlimited_context.setCheckState(Qt.CheckState.Checked)
        self.llm_context_length = QLineEdit(self.settings.value('llm/server/context') if self.settings.contains('llm/server/context') else '4096', self.llm_settings_group_box)
        self.llm_context_length.setValidator(QIntValidator())
        port_num_size = font_meter.size(0, 'NNNNN').width()
        self.llm_context_length.setFixedWidth(port_num_size)
        self.llm_server_cache_prompt = QCheckBox('Cache prompt', self.llm_settings_group_box)
        if self.settings.contains('llm/server/cache_prompt'):
            self.llm_server_cache_prompt.setCheckState(Qt.CheckState.Checked if self.settings.value('llm/server/cache_prompt') == 'CheckState.Checked' else Qt.CheckState.Unchecked)
        # LLM server control triggers
        self.llm_server_run_btn = QPushButton('Run local LLM server', self.llm_settings_group_box)
        self.llm_server_run_btn.clicked.connect(self.llm_server_run)
        self.llm_server_connect_test_btn = QPushButton('Test LLM server connection', self.llm_settings_group_box)
        self.llm_server_connect_test_btn.clicked.connect(self.test_llm_server_connect)
        self.llm_settings_set_local_btn = QPushButton('Set local', self.llm_settings_group_box)
        self.llm_settings_set_local_btn.clicked.connect(self.set_llm_settings_local)
        self.llm_server_use_https = QCheckBox('Use HTTPS (remote only)', self.llm_settings_group_box)
        if self.settings.contains('llm/server/https'):
            self.llm_server_use_https.setCheckState(Qt.CheckState.Checked if self.settings.value('llm/server/https') == 'CheckState.Checked' else Qt.CheckState.Unchecked)
        self.llm_server_stop_btn = QPushButton('Stop local LLM server', self.llm_settings_group_box)
        self.llm_server_stop_btn.clicked.connect(self.llm_server_stop)
        # Grid layout
        llm_settings_group_box_layout.addWidget(llm_server_executable_label, 0, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_executable, 0, 1)
        llm_settings_group_box_layout.addWidget(self.llm_server_executable_btn, 0, 2)
        llm_settings_group_box_layout.addWidget(llm_server_uri_label, 1, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_uri, 1, 1)
        llm_settings_group_box_layout.addWidget(self.llm_server_port, 1, 2)
        llm_settings_group_box_layout.addWidget(llm_server_api_key_label, 2, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_api_key, 2, 1)
        llm_settings_group_box_layout.addWidget(self.llm_server_auth, 2, 2)
        llm_settings_group_box_layout.addWidget(llm_server_model_label, 3, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_model, 3, 1)
        llm_settings_group_box_layout.addWidget(self.llm_server_model_btn, 3, 2)
        llm_settings_group_box_layout.addWidget(llm_server_mmproj_label, 4, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_mmproj, 4, 1)
        llm_settings_group_box_layout.addWidget(self.llm_server_mmproj_btn, 4, 2)
        llm_settings_group_box_layout.addWidget(llm_server_mtp_label, 5, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_mtp, 5, 1)
        llm_settings_group_box_layout.addWidget(self.llm_server_mtp_btn, 5, 2)
        llm_settings_group_box_layout.addWidget(self.llm_server_cache_prompt, 6, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_unlimited_context, 6, 1)
        llm_settings_group_box_layout.addWidget(self.llm_context_length, 6, 2)
        llm_settings_group_box_layout.addWidget(self.llm_server_run_btn, 7, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_connect_test_btn, 7, 1)
        llm_settings_group_box_layout.addWidget(self.llm_settings_set_local_btn, 7, 2)
        llm_settings_group_box_layout.addWidget(self.llm_server_use_https, 8, 0)
        llm_settings_group_box_layout.addWidget(self.llm_server_stop_btn, 8, 1)
        llm_settings_group_box_layout.addWidget(self.llm_server_use_mmap, 8, 2)
        # System group
        self.system_settings_group_box = QGroupBox('System settings', self.settings_tab)
        settings_layout.addWidget(self.system_settings_group_box)
        system_settings_group_box_layout = QGridLayout(self.system_settings_group_box)
        # Icon size
        icon_size_label = QLabel('List icon size [px]:', self.system_settings_group_box)
        self.icon_size_slider = QSlider(Qt.Orientation.Horizontal, self.system_settings_group_box)
        self.icon_size_slider.setRange(50,300)
        self.icon_size_slider.setSingleStep(1)
        self.icon_size_slider.valueChanged.connect(self.update_icon_size)
        self.icon_size_value_label = QLabel('100', self.system_settings_group_box)
        # Application timeout (LLM server)
        app_timeout_label = QLabel('Application timeout [ms]:', self.system_settings_group_box)
        self.app_timeout_slider = QSlider(Qt.Orientation.Horizontal, self.system_settings_group_box)
        self.app_timeout_slider.setRange(1000,30000)
        self.app_timeout_slider.setSingleStep(100)
        self.app_timeout_slider.setPageStep(1000)
        self.app_timeout_slider.valueChanged.connect(self.update_app_timeout)
        self.app_timeout_value_label = QLabel('3000', self.system_settings_group_box)
        self.app_timeout_slider.setValue(self.app_timeout)
        # Autosave flag
        self.autosave_generated = QCheckBox('Auto store metadata', self.system_settings_group_box)
        if self.settings.contains('autosave'):
            self.autosave_generated.setCheckState(Qt.CheckState.Checked if self.settings.value('autosave') == 'CheckState.Checked' else Qt.CheckState.Unchecked)
        # Pre-truncate flag
        self.pre_truncate = QCheckBox('Truncate existing metadata', self.system_settings_group_box)
        if self.settings.contains('pre_truncate'):
            self.pre_truncate.setCheckState(Qt.CheckState.Checked if self.settings.value('pre_truncate') == 'CheckState.Checked' else Qt.CheckState.Unchecked)
        # Auto overwrite flag
        self.auto_overwrite = QCheckBox('Overwrite', self.system_settings_group_box)
        if self.settings.contains('auto_overwrite'):
            self.auto_overwrite.setCheckState(Qt.CheckState.Checked if self.settings.value('auto_overwrite') == 'CheckState.Checked' else Qt.CheckState.Unchecked)
        # Grid layout
        system_settings_group_box_layout.addWidget(icon_size_label, 0, 0)
        system_settings_group_box_layout.addWidget(self.icon_size_slider, 0, 1)
        system_settings_group_box_layout.addWidget(self.icon_size_value_label, 0, 2)
        system_settings_group_box_layout.addWidget(app_timeout_label, 1, 0)
        system_settings_group_box_layout.addWidget(self.app_timeout_slider, 1, 1)
        system_settings_group_box_layout.addWidget(self.app_timeout_value_label, 1, 2)
        system_settings_group_box_layout.addWidget(self.auto_overwrite, 2, 0)
        system_settings_group_box_layout.addWidget(self.autosave_generated, 2, 2)
        system_settings_group_box_layout.addWidget(self.pre_truncate, 2, 1)
        # Prompts group
        self.prompt_settings_group_box = QGroupBox('Prompt', self.settings_tab)
        settings_layout.addWidget(self.prompt_settings_group_box)
        prompt_settings_group_box_layout = QVBoxLayout(self.prompt_settings_group_box)
        self.llm_main_prompt_window = QPlainTextEdit(self.prompt_settings_group_box)
        prompt_settings_group_box_layout.addWidget(self.llm_main_prompt_window)
        self.llm_main_prompt_window.setFont(mono_font)
        self.llm_main_prompt_window.setReadOnly(False)
        self.llm_main_prompt_window.setPlainText(base64.b64decode(self.settings.value('llm/main_prompt').encode('ascii')).decode('utf-8') if self.settings.contains('llm/main_prompt') else short_default_prompt)
# Log panel
        log_layout = QVBoxLayout(self.log_tab)
        # LLM server
        self.llm_log_group_box = QGroupBox('LLM server', self.log_tab)
        log_layout.addWidget(self.llm_log_group_box)
        llm_log_group_box_layout = QVBoxLayout(self.llm_log_group_box)
        self.llm_log_window = QPlainTextEdit(self.llm_log_group_box)
        llm_log_group_box_layout.addWidget(self.llm_log_window)
        self.llm_log_window.setFont(mono_font)
        self.llm_log_window.setReadOnly(True)
        self.llm_log_window.setCenterOnScroll(True)
        # Generation logger
        self.generation_log_group_box = QGroupBox('Generation', self.log_tab)
        log_layout.addWidget(self.generation_log_group_box)
        generation_log_group_box_layout = QVBoxLayout(self.generation_log_group_box)
        self.generation_log_window = QPlainTextEdit(self.generation_log_group_box)
        generation_log_group_box_layout.addWidget(self.generation_log_window)
        self.generation_log_window.setFont(mono_font)
        self.generation_log_window.setReadOnly(True)
        self.generation_log_window.setCenterOnScroll(True)
# Settings init
        if self.settings.contains('geometry'):
            self.restoreGeometry(self.settings.value('geometry'))
        if self.settings.contains('window_state'):
            self.restoreState(self.settings.value('window_state'))
        if self.settings.contains('main_splitter_state'):
            self.main_splitter.restoreState(self.settings.value('main_splitter_state'))
        if self.settings.contains('last_directory'):
            self.last_directory = self.settings.value('last_directory')
        if self.settings.contains('icon_size'):
            self.update_icon_size(int(self.settings.value('icon_size')))
            self.icon_size_slider.setValue(self.icon_size)
            self.images_list.setIconSize(QSize(self.icon_size, self.icon_size))
        if self.settings.contains('app_timeout'):
            self.update_app_timeout(int(self.settings.value('app_timeout')))
            self.app_timeout_slider.setValue(self.app_timeout)

# GUI handler functions
    def enumerate_directory(self):
        probe_string = QFileDialog.getExistingDirectory(self, 'Select Directory', str(self.last_directory))
        probe_directory = Path(probe_string).resolve() if probe_string else None
        if probe_directory is None:
            return
        if not self.profiler.probe_directory(probe_directory):
            self.error_message_dialog.setText('No supported graphic files found!')
            self.error_message_dialog.exec()
        else:
            self.update_photographs_list()
            self.statusBar().showMessage('Loaded {} images'.format(str(len(self.profiler.photographs_list))))
            self.last_directory = probe_directory

    def select_photograph(self, item, prev_item):
        if item is not None:
            self.statusBar().showMessage('Loading metadata from {}'.format(item.text()))
            self.statusBar().repaint()
            sections = self.update_metadata(item.data(Qt.ItemDataRole.UserRole))
            self.statusBar().showMessage('Loaded {} metadata from {}'.format(str(sections), item.text()))

    def clear_metadata(self):
        if self.profiler.index != -1 and self.images_list.currentIndex().isValid():
            item = self.images_list.model().index(self.images_list.currentIndex().row())
            self.statusBar().showMessage('Requested metadata deletion from {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))
            self.statusBar().repaint()
            self.question_dialog.setText('Do you really want to clear the metadata?')
            self.question_dialog.setInformativeText('The metadata deletion cannot be undone!')
            self.question_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            self.question_dialog.setIcon(QMessageBox.Icon.Question)
            if self.question_dialog.exec() == QMessageBox.StandardButton.Yes:
                self.profiler.clear_metadata()
                self.statusBar().showMessage('Deleted metadata from {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))
                self.update_metadata(item.data(Qt.ItemDataRole.UserRole))
                self.statusBar().repaint()
            else:
                self.statusBar().showMessage('Cancelled metadata deletion from {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))
                self.statusBar().repaint()

    def truncate_metadata(self):
        if self.profiler.index != -1 and self.images_list.currentIndex().isValid():
            item = self.images_list.model().index(self.images_list.currentIndex().row())
            self.statusBar().showMessage('Requested metadata truncation from {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))
            self.statusBar().repaint()
            self.profiler.truncate_metadata()
            self.statusBar().showMessage('Truncated metadata from {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))

    def select_llm_server_executable(self):
        llm_executable_string = QFileDialog.getOpenFileName(self, 'Select llama.cpp Server Executable', '', 'llama.cpp server executable (llama-server*)', '', QFileDialog.Option.ReadOnly)[0]
        llm_executable = Path(llm_executable_string).resolve() if llm_executable_string else None
        if llm_executable is None:
            return
        self.llm_server_executable.setText(str(llm_executable))

    def select_llm_server_model(self):
        llm_model_string = QFileDialog.getOpenFileName(self, 'Select GGUF model file', '', 'GGUF model file (*.gguf)', '', QFileDialog.Option.ReadOnly)[0]
        llm_model = Path(llm_model_string).resolve() if llm_model_string else None
        if llm_model is None:
            return
        self.llm_server_model.setText(str(llm_model))

    def select_llm_server_mmproj(self):
        llm_mmproj_string = QFileDialog.getOpenFileName(self, 'Select GGUF MMPROJ file', str(Path(self.llm_server_model.text()).parent) if Path(self.llm_server_model.text()).is_file() else '', 'GGUF multimodal projector file (*.gguf)', '', QFileDialog.Option.ReadOnly)[0]
        llm_mmproj = Path(llm_mmproj_string).resolve() if llm_mmproj_string else None
        if llm_mmproj is None:
            return
        self.llm_server_mmproj.setText(str(llm_mmproj))

    def select_llm_server_mtp(self):
        llm_mtp_string = QFileDialog.getOpenFileName(self, 'Select GGUF MTP draft file', str(Path(self.llm_server_model.text()).parent) if Path(self.llm_server_model.text()).is_file() else '', 'GGUF MTP draft file (*.gguf)', '', QFileDialog.Option.ReadOnly)[0]
        llm_mtp = Path(llm_mtp_string).resolve() if llm_mtp_string else None
        if llm_mtp is None:
            return
        self.llm_server_mtp.setText(str(llm_mtp))

    def llm_server_run(self):
        if not Path(self.llm_server_executable.text()).resolve().is_file():
            self.error_message_dialog.setText('Invalid local server executable!')
            self.error_message_dialog.exec()
            return
        self.have_server = True
        if not Path(self.llm_server_model.text()).resolve().is_file():
            self.error_message_dialog.setText('Invalid LLM model path!')
            self.error_message_dialog.exec()
            return
        self.have_model = True
        if not Path(self.llm_server_mmproj.text()).resolve().is_file():
            self.error_message_dialog.setText('Invalid LLM multimodal projector path!')
            self.error_message_dialog.exec()
            return
        self.have_mmproj = True
        if not Path(self.llm_server_mtp.text()).resolve().is_file():
            pass
            self.statusBar().showMessage('Invalid LLM MTP draft model path {}!'.format(str(Path(self.llm_server_mtp.text()).resolve())))
        else:
            self.have_mtp = True
        if self.llm_server_process is not None:
            self.question_dialog.setText('Restart the local LLM server?')
            self.question_dialog.setInformativeText('Local LLM server is already running!')
            self.question_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            self.question_dialog.setIcon(QMessageBox.Icon.Question)
            if self.question_dialog.exec() == QMessageBox.StandardButton.Yes:
                self.llm_server_stop()
            else:
                return
        self.llm_server_process = QProcess()
        self.llm_server_process.readyReadStandardOutput.connect(self.log_llm_stdout)
        self.llm_server_process.readyReadStandardError.connect(self.log_llm_stderr)
        llm_server_arguments = [
            '--model', str(Path(self.llm_server_model.text()).resolve()),
            '--mmproj', str(Path(self.llm_server_mmproj.text()).resolve()),
            '--host', self.llm_server_uri.text(),
            '--port', self.llm_server_port.text(),
            '--no-cache-prompt' if self.llm_server_cache_prompt.checkState() == Qt.CheckState.Unchecked else '--cache-prompt'
        ]
        if self.have_mtp:
            llm_server_arguments += ['--model-draft', str(Path(self.llm_server_mtp.text()).resolve())]
        if self.llm_server_use_mmap.checkState() != Qt.CheckState.Checked:
            llm_server_arguments += ['--no-mmap']
        if self.llm_server_unlimited_context.checkState() == Qt.CheckState.Checked:
            llm_server_arguments += ['--ctx-size', '0']
        else:
            llm_server_arguments += ['--ctx-size', self.llm_context_length.text()]
        self.llm_server_process.start(str(Path(self.llm_server_executable.text()).resolve()), llm_server_arguments)
        self.llm_server_process.waitForStarted(-1)

    def log_llm_stdout(self):
        self.llm_log_window.appendPlainText(bytes(self.llm_server_process.readAllStandardOutput()).decode('utf-8').rstrip())
        self.llm_log_window.ensureCursorVisible()

    def log_llm_stderr(self):
        self.llm_log_window.appendPlainText(bytes(self.llm_server_process.readAllStandardError()).decode('utf-8').rstrip())
        self.llm_log_window.ensureCursorVisible()

    def llm_server_stop(self):
        if self.llm_server_process is not None:
             if self.llm_server_process.state() == QProcess.ProcessState.Running:
                self.llm_server_process.terminate()
                if not self.llm_server_process.waitForFinished(self.app_timeout):
                    self.llm_server_process.kill()
                    self.llm_server_process.waitForFinished()
                del self.llm_server_process
                self.llm_server_process = None

    def set_llm_settings_local(self):
        self.llm_server_uri.setText('127.0.0.1')
        self.llm_server_port.setText('8080')

    def update_icon_size(self, value):
        self.icon_size = int(value)
        self.icon_size_value_label.setText(str(self.icon_size))
        self.images_list.setIconSize(QSize(self.icon_size, self.icon_size))

    def update_app_timeout(self, value):
        self.app_timeout = int(value)
        self.app_timeout_value_label.setText(str(self.app_timeout))

    def save_edited(self):
        metadata_insert = dict()
        if self.description_field.toPlainText() != str():
            metadata_insert['Iptc.Application2.Caption'] = self.description_field.toPlainText()
        if self.title_field.text() != str():
            metadata_insert['Iptc.Application2.ObjectName'] = self.title_field.text()
        if self.keyword_field.text() != str():
            metadata_insert['Iptc.Application2.Keywords'] = self.keyword_field.text()
        if self.profiler.index != -1 and self.images_list.currentIndex().isValid() and any(metadata_insert.values()):
            item = self.images_list.model().index(self.images_list.currentIndex().row())
            self.statusBar().showMessage('Requested metadata edition on {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))
            self.statusBar().repaint()
            self.profiler.update_metadata(metadata_insert)
            self.statusBar().showMessage('Updated metadata on {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))

    def purge_descriptive(self):
        if self.profiler.index != -1 and self.images_list.currentIndex().isValid():
            item = self.images_list.model().index(self.images_list.currentIndex().row())
            self.statusBar().showMessage('Requested descriptive metadata deletion on {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))
            self.statusBar().repaint()
            self.profiler.remove_descriptive_metadata()
            self.title_field.setText(str())
            self.keyword_field.setText(str())
            self.description_field.setPlainText(str())
            self.statusBar().showMessage('Updated metadata on {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))

    def test_llm_server_connect(self):
        self.statusBar().showMessage('Requested LLM server test at {}. Please wait...'.format(self.request_uri('v1/health')))
        http_request = QNetworkRequest(QUrl(self.request_uri('v1/health')))
        http_request.setTransferTimeout(self.app_timeout_slider.value())
        self.request_headers(http_request)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.centralWidget().setEnabled(False)
        response = self.netproc.get(http_request)
        response.finished.connect(self.handle_test_request)

    def process_image(self):
        if self.profiler.index != -1 and self.images_list.currentIndex().isValid():
            item = self.images_list.model().index(self.images_list.currentIndex().row())
            self.statusBar().showMessage('Requested processing: {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))
            self.statusBar().repaint()
            http_request = QNetworkRequest(QUrl(self.request_uri('v1/chat/completions')))
            self.request_headers(http_request)
            self.tabs.setCurrentIndex(2)
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.setEnabled(False)
            response = self.netproc.post(http_request, self.request_formulate())
            response.readyRead.connect(self.handle_image_request_data_segment)
            response.errorOccurred.connect(self.handle_image_request_error)
            sub_event_loop = QEventLoop()
            response.finished.connect(sub_event_loop.quit)
            sub_event_loop.exec()
            self.handle_image_request_finished(response)
            self.generation_log_window.clear()
            self.llm_response = str()

    def process_all(self):
        for i in range(self.images_list.count()):
            item = self.images_list.itemFromIndex(self.images_list.model().index(i))
            self.images_list.setCurrentRow(i, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            self.select_photograph(item, None)
            self.process_image()


# GUI processing helpers
    def update_photographs_list(self):
        self.filename_map.clear()
        self.images_list.clear()
        self.main_progress.setRange(0, len(self.profiler.photographs_list) - 1)
        for c in range(len(self.profiler.photographs_list)):
            f = self.profiler.photographs_list[c]
            self.statusBar().showMessage('Loading {}'.format(str(f)))
            prescaled_icon = QIcon(QPixmap(str(f)).scaledToWidth(self.icon_size, Qt.TransformationMode.SmoothTransformation))
            prescaled_item = QListWidgetItem(prescaled_icon, str(f.name))
            prescaled_item.setData(Qt.ItemDataRole.UserRole, c)
            self.filename_map[prescaled_item.text] = f
            self.images_list.addItem(prescaled_item)
            self.main_progress.setValue(c)
            self.statusBar().repaint()
            self.images_list.repaint()

    def update_metadata(self, index):
        self.metadata_table_model.beginResetModel()
        self.metadata_table_model.data.clear()
        metadata = self.profiler.load_metadata(index)
        metadata_sections = list(metadata.keys())
        if metadata_sections:
            for section in metadata_sections:
                self.metadata_table_model.data.append((section, str()))
                for param in metadata[section].items():
                    self.metadata_table_model.data.append(param)
        self.metadata_table_model.endResetModel()
        if 'IPTC' in metadata.keys():
            if 'Iptc.Application2.ObjectName' in metadata['IPTC'].keys():
                self.title_field.setText(metadata['IPTC']['Iptc.Application2.ObjectName'])
            else:
                self.title_field.setText(str())
            if 'Iptc.Application2.Keywords' in metadata['IPTC'].keys():
                self.keyword_field.setText(', '.join(metadata['IPTC']['Iptc.Application2.Keywords']))
            else:
                self.keyword_field.setText(str())
            if 'Iptc.Application2.Caption' in metadata['IPTC'].keys():
                self.description_field.setPlainText(metadata['IPTC']['Iptc.Application2.Caption'])
            else:
                self.description_field.setPlainText(str())
        else:
            self.title_field.setText(str())
            self.keyword_field.setText(str())
            self.description_field.setPlainText(str())
        return metadata_sections

    def save_settings(self):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('window_state', self.saveState())
        self.settings.setValue('main_splitter_state', self.main_splitter.saveState())
        self.settings.setValue('last_directory', self.last_directory)
        self.settings.setValue('llm/server/executable', self.llm_server_executable.text())
        self.settings.setValue('llm/server/key', self.llm_server_api_key.text())
        self.settings.setValue('llm/server/auth', str(self.llm_server_auth.checkState()))
        self.settings.setValue('llm/server/model', self.llm_server_model.text())
        self.settings.setValue('llm/server/mmproj', self.llm_server_mmproj.text())
        self.settings.setValue('llm/server/mtp', self.llm_server_mtp.text())
        self.settings.setValue('llm/server/uri', self.llm_server_uri.text())
        self.settings.setValue('llm/server/port', self.llm_server_port.text())
        self.settings.setValue('llm/server/mmap', str(self.llm_server_use_mmap.checkState()))
        self.settings.setValue('llm/server/unlimited_context', str(self.llm_server_unlimited_context.checkState()))
        self.settings.setValue('llm/server/context', self.llm_context_length.text())
        self.settings.setValue('llm/server/https', str(self.llm_server_use_https.checkState()))
        self.settings.setValue('llm/main_prompt', base64.b64encode(self.llm_main_prompt_window.toPlainText().encode('utf-8')).decode('ascii'))
        self.settings.setValue('icon_size', str(self.icon_size_slider.value()))
        self.settings.setValue('app_timeout', str(self.app_timeout_slider.value()))
        self.settings.setValue('autosave', str(self.autosave_generated.checkState()))
        self.settings.setValue('pre_truncate', str(self.pre_truncate.checkState()))
        self.settings.setValue('auto_overwrite', str(self.auto_overwrite.checkState()))
        self.settings.setValue('llm/server/cache_prompt', str(self.llm_server_cache_prompt.checkState()))

    def request_uri(self, endpoint=str()):
        return 'http{}://{}:{}/{}'.format('s' if self.llm_server_use_https.checkState() == Qt.CheckState.Checked else str(), self.llm_server_uri.text(), self.llm_server_port.text(), endpoint)
        
    def request_headers(self, request: QNetworkRequest):
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
        if self.llm_server_auth.checkState() == Qt.CheckState.Checked:
            request.setRawHeader('Authorization'.encode('ascii'), 'Bearer {}'.format(self.llm_server_api_key.text()).encode('ascii'))

    def request_formulate(self):
        title_addendum = '\nPlease use the existing image title as a hint: {}'.format(self.title_field.text())
        req = {
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': self.llm_main_prompt_window.toPlainText() + (title_addendum if len(self.title_field.text()) > 0 else str())
                        },
                        {
                            'type': 'image_url',
                            'image_url': {'url': self.profiler.base64_llm_data()}
                        }
                    ]
                }
            ],
            'cache_prompt': False,
            'stream': True,
            'reasoning_effort': 'none',
            'chat_template_kwargs': {
                'enable_thinking': False
            }
        }
        return QJsonDocument(req).toJson(QJsonDocument.JsonFormat.Compact)

    def handle_test_request(self):
        response = self.sender()
        QApplication.restoreOverrideCursor()
        self.centralWidget().setEnabled(True)
        if response.error() == QNetworkReply.NetworkError.NoError:
            self.statusBar().showMessage('LLM Server OK')
            self.llm_log_window.appendPlainText(response.readAll().data().decode('utf-8'))
            return
        else:
            self.error_message_dialog.setText('LLM server at {} is not running or it is not ready!'.format(self.request_uri('v1/health')))
            self.statusBar().showMessage('LLM server at {} is not running or it is not ready!'.format(self.request_uri('v1/health')))
            self.error_message_dialog.exec()
        response.deleteLater()

    def handle_image_request_error(self):
        response = self.sender()
        self.error_message_dialog.setText('LLM server error: {}'.format(response.errorString()))
        self.statusBar().showMessage('LLM server error!')
        self.error_message_dialog.exec()

    def handle_image_request_data_segment(self):
        response = self.sender()
        tokens = response.readAll().data().decode('utf-8').split('\n\n')
        for token_desc in tokens:
            token = QJsonDocument().fromJson(token_desc[6:].encode('utf-8'))
            if not token['choices'][0]['delta']['content'].isNull():
                generated = token['choices'][0]['delta']['content'].toString()
                self.llm_response += generated
                self.generation_log_window.insertPlainText(generated)
                self.generation_log_window.ensureCursorVisible()
                self.statusBar().showMessage('Generated: [ {} ]'.format(generated))
                self.findChild(QToolBar, 'MainToolbar').repaint()

    def handle_image_request_finished(self, response):
        # response = self.sender()
        QApplication.restoreOverrideCursor()
        self.setEnabled(True)
        item = self.images_list.model().index(self.images_list.currentIndex().row())
        self.statusBar().showMessage('Succesfully processed {}'.format(item.data(Qt.ItemDataRole.DisplayRole)))
        self.statusBar().repaint()
        response_json = QJsonDocument().fromJson(self.llm_response.encode('utf-8'))
        if response_json.isEmpty() or response_json['keywords'].isUndefined() or not response_json['keywords'].isArray() or response_json['title'].isUndefined() or response_json['description'].isUndefined():
            self.error_message_dialog.setText('Generation error: the returned JSON object is invalid. Please try to correct the prompt!')
            self.statusBar().showMessage('Generation error!')
            self.error_message_dialog.exec()
        else:
            keywords_list = ','.join(word.toString() for word in response_json['keywords'].toArray())
            if self.auto_overwrite.checkState() == Qt.CheckState.Unchecked and (len(self.keyword_field.text()) > 0 or len(self.title_field.text()) > 0 or len(self.description_field.toPlainText()) > 0):
                self.question_dialog.setText('Do you want to overwrite existing metadata with the generated one?')
                self.question_dialog.setInformativeText('The descriptive metadata exists already in this image!')
                self.question_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                self.question_dialog.setIcon(QMessageBox.Icon.Question)
                if self.question_dialog.exec() == QMessageBox.StandardButton.No:
                    return
            self.keyword_field.setText(keywords_list)
            if not len(self.title_field.text()) > 0:
                self.title_field.setText(response_json['title'].toString())
            self.description_field.setPlainText(response_json['description'].toString())
            self.tabs.setCurrentIndex(0)
            if self.autosave_generated.checkState() == Qt.CheckState.Checked:
                if self.pre_truncate.checkState() == Qt.CheckState.Checked:
                    self.truncate_metadata()
                self.save_edited()
            else:
                self.question_dialog.setText('Do you want to write the generated metadata into the image?')
                self.question_dialog.setInformativeText('The generated metadata will replace the original metadata if it existed!')
                self.question_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                self.question_dialog.setIcon(QMessageBox.Icon.Question)
                if self.question_dialog.exec() == QMessageBox.StandardButton.Yes:
                    if self.pre_truncate.checkState() == Qt.CheckState.Checked:
                        self.truncate_metadata()
                    self.save_edited()
        response.deleteLater()

# System level functions
    def closeEvent(self, event):
        self.save_settings()
        if self.llm_server_process is not None:
            self.llm_server_stop()

# Profiler
profiler_api = Profiler()

# QT Event Loop Runner
app = QApplication(sys.argv)
window = ProfilerWindow(profiler_api)
window.show()
sys.exit(app.exec())
