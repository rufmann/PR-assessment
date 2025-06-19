import os
import sys
import unreal
from unreal import Paths, EditorAssetLibrary
from importlib import reload
from functools import partial

import ue_utils

from PySide6.QtWidgets import (QWidget, QDialog, QApplication, QHBoxLayout, QVBoxLayout, 
                               QListWidget, QPushButton, QLabel, QSpacerItem, QSizePolicy, 
                               QLineEdit, QFileDialog, QAbstractItemView, QMessageBox, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLineEdit)
from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QDropEvent

class SelectSkeletonDialog(QDialog):
    def __init__(self, all_skeletons):
        super().__init__()
        self.all_skeletons = all_skeletons
        self.selected_skeleton = None
        self.setWindowTitle("Choose Skeleton")
        self.setFixedWidth(600)
        self.label = QLabel("Skeletons needed to import anim. Please select any one of skeleton below:")
        self.main_layout = QVBoxLayout()
        self.buttons_layout = QHBoxLayout()
        self.select_button = QPushButton("Select Skeleton")
        self.cancel_button = QPushButton("Cancel")
        self.skel_list_widget = QListWidget()
        self.skel_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for skel in self.all_skeletons:
            self.skel_list_widget.addItem(skel.split('.')[0])

        self.buttons_layout.addWidget(self.select_button)
        self.buttons_layout.addWidget(self.cancel_button)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.skel_list_widget)
        self.main_layout.addLayout(self.buttons_layout)
        self.setLayout(self.main_layout)

        self.select_button.clicked.connect(self.select_skeleton)
        self.cancel_button.clicked.connect(self.abort_selection)

    def select_skeleton(self):
        self.selected_skeleton = self.skel_list_widget.selectedItems()[0].text()
        print(self.selected_skeleton)
        self.accept()

    def abort_selection(self):
        self.reject()

class ExistingAssetsDialog(QDialog):
    def __init__(self, assets):
        super().__init__()
        self.result = None
        self.assets = assets
        self.setWindowTitle("Existing assets found.")
        # self.setFixedWidth(300)
        self.main_layout = QVBoxLayout()
        self.list_layout = QVBoxLayout()
        self.buttons_layout = QHBoxLayout()
        self.description_text = QLabel("These assets are already imported.\nPlease choose operation.")
        self.reimport_button = QPushButton("Re-import")
        self.import_button = QPushButton("Import")
        self.cancel_button = QPushButton("Cancel")
        
        for asset in self.assets:
            asset_name = os.path.basename(asset).strip('.fbx')
            label = QLabel(f" - {asset_name}")
            self.list_layout.addWidget(label)
        
        self.buttons_layout.addWidget(self.reimport_button)
        self.buttons_layout.addWidget(self.import_button)
        self.buttons_layout.addWidget(self.cancel_button)

        self.main_layout.addWidget(self.description_text)
        self.main_layout.addLayout(self.list_layout)
        self.main_layout.addLayout(self.buttons_layout)
        self.setLayout(self.main_layout)

        self.reimport_button.clicked.connect(self.do_reimport)
        self.import_button.clicked.connect(self.do_import)
        self.cancel_button.clicked.connect(self.do_abort)

        # self.exec()

    def do_import(self):
        self.result = "import"
        self.accept()
    
    def do_reimport(self):
        self.result = "replace"
        self.accept()

    def do_abort(self):
        # self.result = "abort"
        self.reject()

class AssetListWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Asset Name", "Source Path"])
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path:
                    self.addItem(file_path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            selected_rows = set()
            for item in self.selectedItems():
                selected_rows.add(item.row())
            
            for row in sorted(selected_rows, reverse=True):
                self.removeRow(row)
    
    def addItem(self, file_path):
        asset_name = os.path.basename(file_path).strip('.fbx')
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(asset_name))
        self.setItem(row, 1, QTableWidgetItem(file_path))

class UEAssetImporter(QWidget):
    def __init__(self):
        super(UEAssetImporter, self).__init__()
        self.PROJECT_ROOT = Paths.project_dir()
        self.CONTENT_ROOT = Paths.project_content_dir()
        self.GAME_ROOT = "/Game"
        self.destination_path = self.GAME_ROOT  # default path /Game/Content
        self.init_ui()
        self.callbacks()
    
    def init_ui(self):
        self.setFixedSize(600, 400)
        self.setWindowTitle("PR Assessment Subject_2 - UE Asset Importer")

        self.main_layout = QVBoxLayout()
        self.browse_layout = QHBoxLayout()
        self.buttons_layout = QHBoxLayout()
        self.asset_list_widget = AssetListWidget()
        self.add_assets_button = QPushButton("[+]Add asset")
        self.remove_assets_button = QPushButton("[-]Remove asset")
        self.destination_path_label = QLabel("Import to: ")
        self.destination_path_line_edit = QLineEdit()
        self.destination_path_line_edit.setClearButtonEnabled(True)
        self.destination_path_browse_button = QPushButton("...")
        self.destination_path_browse_button.setFixedWidth(40)
        self.destination_path_browse_button.setToolTip("Browse import path")
        self.import_button = QPushButton("Import")
        self.close_button = QPushButton("Exit")

        spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.browse_layout.addWidget(self.add_assets_button)
        self.browse_layout.addWidget(self.remove_assets_button)
        self.browse_layout.addSpacerItem(spacer)
        
        self.buttons_layout.addWidget(self.destination_path_label)
        self.buttons_layout.addWidget(self.destination_path_line_edit)
        self.buttons_layout.addWidget(self.destination_path_browse_button)
        self.buttons_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.buttons_layout.addWidget(self.close_button)
        self.buttons_layout.addWidget(self.import_button)
        
        self.main_layout.addLayout(self.browse_layout)
        self.main_layout.addWidget(self.asset_list_widget)
        self.main_layout.addLayout(self.buttons_layout)

        self.setLayout(self.main_layout)

    def callbacks(self):
        self.add_assets_button.clicked.connect(partial(self.open_file_browser, path=self.PROJECT_ROOT, type="file"))
        self.destination_path_browse_button.clicked.connect(partial(self.open_file_browser, path=self.CONTENT_ROOT, type="dir"))
        self.remove_assets_button.clicked.connect(self.remove_assets)
        self.import_button.clicked.connect(self.do_imports)
        self.close_button.clicked.connect(self.close)        

    def get_all_listed_assets(self):
        all_assets = list()
        for i in range(self.asset_list_widget.rowCount()):
            item = self.asset_list_widget.item(i, 1)
            all_assets.append(item.text())
        return all_assets

    def open_file_browser(self, path=None, type=None):
        current_items = self.get_all_listed_assets()
        print(current_items)
        if type == "file":
            file_paths = QFileDialog.getOpenFileNames(self, "Select Asset Files", path, "3D assets (*.obj, *.fbx)")[0]
            for path in file_paths:
                if path not in current_items:
                    self.asset_list_widget.addItem(path)
        elif type == "dir":
            selected_dir = QFileDialog.getExistingDirectory(self, "Select Destination Folder", path, options=QFileDialog.Option.ShowDirsOnly)
            if selected_dir:
                self.destination_path = ue_utils.to_game_path(selected_dir)
                in_game_path = self.destination_path.replace("/Game", "/All/Content")
                self.destination_path_line_edit.setText(in_game_path)
                print(self.destination_path)
                self.destination_path_line_edit.setCursorPosition(0)

    def remove_assets(self):
        print("removing assets")
        selected_rows = set()
        for item in self.asset_list_widget.selectedItems():
            selected_rows.add(item.row())
        
        for row in sorted(selected_rows, reverse=True):
            self.asset_list_widget.removeRow(row)

    def do_validate_skm(self):
        unreal.log("Validating Skeletons")

        dialog = QDialog()
        # dialog.setFixedWidth(500)
        dialog.setWindowTitle("Asset Validation")
        result_label = QLabel()
        result_label.setWordWrap(True)
        main_layout = QVBoxLayout()
        ok_btn = QPushButton("OK")
        
        # load skeleton objects
        all_skeleton = [sk for sk in ue_utils.get_all_assets(self.GAME_ROOT) if 'Skeleton' in sk]
        result = ue_utils.validate_skeleton(all_skeleton)
        if result:
            if isinstance(result, str):
                result_label.setText(result)
            if isinstance(result, tuple):
                result_str = ""
                msg, skel_groups = result
                for index, (bone_count, skel_names) in enumerate(skel_groups.items(), start=1):
                    skel_names = "\n".join([f"  - {name.split('.')[0]}" for name in skel_names])
                    if index > 1:
                        result_str += "\n" * 2                    
                    result_str += f"""[Skeleton with bone count: {bone_count}]\n{skel_names}"""
                result_label.setText(result_str)

        main_layout.addWidget(result_label)
        main_layout.addWidget(ok_btn)
        dialog.setLayout(main_layout)

        ok_btn.clicked.connect(dialog.accept)
        dialog.exec()

    def do_import_skm(self):
        print("\nStarting Skeleton Import Process")
        tasks = list()
        existing_assets = list()
        cb_assets = [os.path.basename(asset).split('.')[-1] for asset in ue_utils.get_all_assets(self.GAME_ROOT) if 'SKM_' in asset and 'Skeleton' not in asset and 'Physic' not in asset]
        # import skm assets process
        skm_list = [skm for skm in self.get_all_listed_assets() if 'SKM_' in skm]
        for asset in skm_list:
            if os.path.basename(asset).strip('.fbx') in cb_assets:
                existing_assets.append(asset)
            else:
                # import new skm assets
                print(f"[SKM import] {asset} not yet imported. Importing")
                if self.destination_path:
                    task = ue_utils.skeletal_mesh_import_task(asset, mode='import', destination_path=self.destination_path)
                    tasks.append(task)
        # import or reimport skm assets
        if existing_assets:
            unreal.log("Existing skeletons found")
            dialog = ExistingAssetsDialog(existing_assets)
            if dialog.exec() == QDialog.Accepted:
                mode = dialog.result
                for asset in existing_assets:
                    print(f"{mode}ing {asset}")
                    task = ue_utils.skeletal_mesh_import_task(asset, mode=mode, destination_path=self.destination_path)
                    tasks.append(task)
            else:
                self.close()
                return "abort"

        if tasks:
            asset_tools = ue_utils.get_asset_tools()
            asset_tools.import_asset_tasks(tasks)

        self.do_validate_skm()

        for asset in self.get_all_listed_assets():
            if 'ANIM' in asset:
                self.do_import_anim_seq()
                break
    
    def do_import_anim_seq(self):
        unreal.log("\nStarting Anim Sequence Import Process")
        tasks = list()
        existing_assets = list()
        cb_assets = ue_utils.get_all_assets(self.GAME_ROOT)
        all_skeletons = [skel for skel in cb_assets if 'Skeleton' in skel]
        if all_skeletons:
            dialog = SelectSkeletonDialog(all_skeletons)
            if dialog.exec() == QDialog.Accepted:
                skeleton = unreal.load_object(None, dialog.selected_skeleton)
                anim_list = [anim for anim in self.get_all_listed_assets() if 'ANIM_' in anim]
                cb_anim_assets = [unreal.load_object(None, anim).get_name() for anim in cb_assets if 'ANIM' in anim]
                for asset in anim_list:
                    if os.path.basename(asset).strip('.fbx') in cb_anim_assets:
                        existing_assets.append(asset)
                    else:
                        # import new anim seq assets
                        print(f"{asset} not yet imported. Importing")
                        task = ue_utils.anim_sequence_import_task(asset, skeleton, mode='import', destination_path=self.destination_path)
                        tasks.append(task)

                # import or reimport anim seq assets
                if existing_assets:
                    unreal.log("Existing animations found")
                    dialog = ExistingAssetsDialog(existing_assets)
                    if dialog.exec() == QDialog.Accepted:
                        mode = dialog.result
                        for asset in existing_assets:
                            print(f"{mode}ing {asset}")
                            task = ue_utils.anim_sequence_import_task(asset, skeleton, mode=mode, destination_path=self.destination_path)
                            tasks.append(task)
                    else:
                        dialog.close()
            else:
                message = QMessageBox.critical(self, "Aborting import", "Skeleton not selected.\nAborting import.", QMessageBox.Ok)
            
        if tasks:
            asset_tools = ue_utils.get_asset_tools()
            asset_tools.import_asset_tasks(tasks)

    def import_preview(self):
        dialog = QDialog()
        dialog.setWindowTitle("Import Preview")
        label = QLabel("The following assets will be imported:")
        main_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        in_game_path = self.destination_path.replace("/Game", "/All/Content")

        main_layout.addWidget(label)
        for i in range(self.asset_list_widget.rowCount()):
            item = self.asset_list_widget.item(i, 0)    
            item_label = QLabel(f"{item.text()} ==> {in_game_path}/{item.text()}")
            main_layout.addWidget(item_label)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
        dialog.setLayout(main_layout)

        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        return dialog.exec()

    def do_post_process(self):
        """
        Post-processes can be added here like renaming, asset validation, etc.
        """
        asset_prefix_map = {'SkeletalMesh': 'SKM', 'Skeleton': 'SKL', 'PhysicsAsset': 'PA', 'Material': 'M', 'AnimSequence': 'ANIM'}
        cb_assets = ue_utils.get_all_assets(self.GAME_ROOT)
        for asset in cb_assets:
            asset_obj = unreal.load_object(None, asset)
            asset_class_name = asset_obj.get_class().get_name()
            if asset_class_name in asset_prefix_map:
                current_name = asset_obj.get_name()
                if '_' in current_name:
                    new_name = current_name.replace(current_name.split('_')[0], asset_prefix_map[asset_class_name])
                else:
                    new_name = f"{asset_prefix_map[asset_class_name]}_{current_name}"
                parent_path = os.path.dirname(asset_obj.get_path_name())
                
                unreal.log(f"Renaming {current_name} to {new_name}")
                EditorAssetLibrary.rename_asset(os.path.join(parent_path, current_name), os.path.join(parent_path, new_name))

    def do_imports(self):
        if not self.get_all_listed_assets():
            message = QMessageBox.critical(self, "Import Asset Error", "No assets detected.\nPlease add assets into the list before importing.", QMessageBox.Ok)
        else:
            if self.destination_path_line_edit.text() != "":
                result = self.import_preview()
                if result == QDialog.Accepted:
                    self.close()
                    self.do_import_skm()
                    self.do_post_process()
                else:
                    print("Import operation aborted.")
            else:
                message = QMessageBox.critical(self, "Import Path Error", "No import path detected.\nPlease enter import path.", QMessageBox.Ok)

def launch_app():
    reload(ue_utils)
    app = QApplication.instance() or QApplication(sys.argv)
    widget = UEAssetImporter()
    widget.show()
    return widget