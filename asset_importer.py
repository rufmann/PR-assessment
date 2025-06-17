import os
import sys
import unreal
from importlib import reload
import ue_utils

from PySide6.QtWidgets import (QWidget, QDialog, QApplication, QHBoxLayout, QVBoxLayout, 
                               QListWidget, QPushButton, QLabel, QSpacerItem, QSizePolicy, 
                               QLineEdit, QFileDialog, QAbstractItemView, QMessageBox, QTableWidget)
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
            self.skel_list_widget.addItem(skel)

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

class AssetListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
    
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
            for item in self.selectedItems():
                self.takeItem(self.row(item))


class UEAssetImporter(QWidget):
    def __init__(self):
        super(UEAssetImporter, self).__init__()
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
        self.import_button = QPushButton("Import")
        self.close_button = QPushButton("Exit")

        spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.browse_layout.addWidget(self.add_assets_button)
        self.browse_layout.addWidget(self.remove_assets_button)
        self.browse_layout.addSpacerItem(spacer)
        
        self.buttons_layout.addSpacerItem(spacer)
        self.buttons_layout.addWidget(self.close_button)
        self.buttons_layout.addWidget(self.import_button)
        
        self.main_layout.addLayout(self.browse_layout)
        self.main_layout.addWidget(self.asset_list_widget)
        self.main_layout.addLayout(self.buttons_layout)

        self.setLayout(self.main_layout)

    def get_all_listed_assets(self):
        return [self.asset_list_widget.item(i).text() for i in range(self.asset_list_widget.count())]

    def callbacks(self):
        self.add_assets_button.clicked.connect(self.open_file_browser)
        self.remove_assets_button.clicked.connect(self.remove_assets)
        self.import_button.clicked.connect(self.do_imports)
        self.close_button.clicked.connect(self.close)        

    def open_file_browser(self):
        current_items = self.get_all_listed_assets()
        file_paths = QFileDialog.getOpenFileNames(self, "Select Asset Files", "", "3D assets (*.obj, *.fbx)")[0]
        for path in file_paths:
            if path not in current_items:
                self.asset_list_widget.addItem(path)

    def remove_assets(self):
        selected_assets = self.asset_list_widget.selectedItems()
        for asset in selected_assets:
            self.asset_list_widget.takeItem(self.asset_list_widget.row(asset))

    def do_validate_skm(self):
        unreal.log("Validating Skeletons")

        dialog = QDialog()
        # dialog.setFixedWidth(500)
        dialog.setWindowTitle("Asset Validation")
        result_label = QLabel()
        result_label.setWordWrap(True)
        main_layout = QVBoxLayout()
        ok_btn = QPushButton("OK")

        # get all skeletons
        # for each skeleton, load skeleton
        # get each skeleton bone number, put in list
        # if there is different bone number in list, ask user to choose which skeleton to use
        # for each skm, use selected skeleton
        
        # load skeleton objects
        all_skeleton = [sk for sk in ue_utils.get_all_assets() if 'Skeleton' in sk]
        result = ue_utils.validate_skeleton(all_skeleton)
        if result:
            if isinstance(result, str):
                result_label.setText(result)
            if isinstance(result, tuple):
                result_str = ""
                msg, skel_groups = result
                for index, (bone_count, skel_names) in enumerate(skel_groups.items(), start=1):
                    skel_names = "\n".join([f"  - {name}" for name in skel_names])
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
        cb_assets = [os.path.basename(asset).split('.')[-1] for asset in ue_utils.get_all_assets() if 'SKM_' in asset and 'Skeleton' not in asset and 'Physic' not in asset]
        # import skm assets process
        for asset in self.get_all_listed_assets():
            if os.path.basename(asset).strip('.fbx') in set([os.path.basename(asset).rsplit('_', 1)[0] for asset in cb_assets]):
                existing_assets.append(asset)
            else:
                # import new skm assets
                print(f"{asset} not yet imported. Importing")
                task = ue_utils.skeletal_mesh_import_task(asset, mode='import')
                tasks.append(task)

        # import or reimport skm assets
        if existing_assets:
            dialog = ExistingAssetsDialog(existing_assets)
            if dialog.exec() == QDialog.Accepted:
                mode = dialog.result
                for asset in existing_assets:
                    print(f"{mode}ing {asset}")
                    task = ue_utils.skeletal_mesh_import_task(asset, mode=mode)
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
        cb_assets = ue_utils.get_all_assets()
        all_skeletons = [skel for skel in cb_assets if 'Skeleton' in skel]
        if all_skeletons:
            dialog = SelectSkeletonDialog(all_skeletons)
            if dialog.exec() == QDialog.Accepted:
                skeleton = unreal.load_object(None, dialog.selected_skeleton)
                anim_list = [anim for anim in self.get_all_listed_assets() if 'ANIM_' in anim]
                for asset in anim_list:
                    if os.path.basename(asset).strip('.fbx') in set([os.path.basename(anim).split('.')[0].rsplit('_', 1)[0] for anim in cb_assets if 'ANIM' in anim]):
                        existing_assets.append(asset)
                    else:
                        # import new anim seq assets
                        print(f"{asset} not yet imported. Importing")
                        task = ue_utils.anim_sequence_import_task(asset, skeleton, mode='import')
                        tasks.append(task)

                # import or reimport anim seq assets
                if existing_assets:
                    dialog = ExistingAssetsDialog(existing_assets)
                    if dialog.exec() == QDialog.Accepted:
                        mode = dialog.result
                        for asset in existing_assets:
                            print(f"{mode}ing {asset}")
                            task = ue_utils.anim_sequence_import_task(asset, skeleton, mode=mode)
                            tasks.append(task)
                    else:
                        dialog.close()
            else:
                message = QMessageBox.critical(self, "Aborting import", "Skeleton not selected.\nAborting import.", QMessageBox.Ok)
            
        if tasks:
            asset_tools = ue_utils.get_asset_tools()
            asset_tools.import_asset_tasks(tasks)

    def do_imports(self):
        self.close()

        self.do_import_skm()
        # self.do_validate_skm()
        # self.do_import_anim_seq()

if __name__ == "__main__":
    reload(ue_utils)
    app = QApplication.instance() or QApplication(sys.argv)
    widget = UEAssetImporter()
    widget.show()

    app.processEvents()
    # sys.exit(app.exec())